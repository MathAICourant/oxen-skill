#!/usr/bin/env python3
"""Run a Wagon question and save its answer and artifact ZIP. Standard library only."""
from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

from oxen_batch import Client, main as batch_main


def main():
    # The complete chunked JSONL workflow also remains available here.
    if len(sys.argv) > 1 and sys.argv[1] in ("validate", "submit", "status", "requests", "cancel", "download"):
        return batch_main(["--base", "https://oxen.lemma.farm/api/v1/wagon/batch", *sys.argv[1:]])
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("question", help="Question text; use --question-file for a file")
    parser.add_argument("--question-file", action="store_true", help="Read the positional argument as a UTF-8 file")
    parser.add_argument("--base", default="https://oxen.lemma.farm/api/v1/wagon")
    parser.add_argument("--model", default="gpt-6.2-sol")
    parser.add_argument("--agent", default="terminus-2")
    parser.add_argument("--environment", default="math-python-v1")
    parser.add_argument("--effort")
    parser.add_argument("--cpu", type=int)
    parser.add_argument("--memory-gib", type=int)
    parser.add_argument("--disk-gib", type=int)
    parser.add_argument("--max-runtime", type=int, default=600, help="Seconds")
    parser.add_argument("--setup-timeout", type=int, default=300, help="Seconds per setup phase")
    parser.add_argument("--max-steps", type=int)
    parser.add_argument("--max-model-calls", type=int)
    parser.add_argument("--max-output-tokens", type=int)
    parser.add_argument("--region")
    parser.add_argument("--network", choices=("none", "public", "allowlist"), default="none")
    parser.add_argument("--allow-host", action="append", default=[])
    parser.add_argument("--output", type=Path, default=Path("wagon-results"))
    parser.add_argument("--no-wait", action="store_true")
    args = parser.parse_args()
    try:
        client = Client(args.base)
        request = {
            "question": Path(args.question).read_text() if args.question_file else args.question,
            "model": args.model, "agent": args.agent, "environment": args.environment,
            "timeouts": {"run_seconds": args.max_runtime, "setup_seconds": args.setup_timeout},
            "network": {"mode": args.network, "allowed_hosts": args.allow_host},
        }
        if args.effort:
            request["reasoning_effort"] = args.effort
        resources = {key: value for key, value in {
            "cpu": args.cpu, "memory_gib": args.memory_gib, "disk_gib": args.disk_gib
        }.items() if value is not None}
        if resources:
            request["resources"] = resources
        limits = {key: value for key, value in {
            "max_steps": args.max_steps, "max_model_calls": args.max_model_calls,
            "max_output_tokens": args.max_output_tokens,
        }.items() if value is not None}
        if limits:
            request["limits"] = limits
        accepted = client.json("/run", "POST", request)
        if args.no_wait:
            print(json.dumps(accepted, indent=2))
            return 0
        run_id = accepted["run_id"]
        end = time.monotonic() + 2 * args.setup_timeout + args.max_runtime + 240
        while True:
            run = client.json("/run/" + run_id)
            if run["state"] not in ("queued", "running") and not run.get("cleanup_pending"):
                break
            if time.monotonic() >= end:
                raise RuntimeError("Polling timed out; run remains available as " + run_id)
            time.sleep(5)
        output = args.output / run_id
        output.mkdir(parents=True, exist_ok=True)
        answer_path = output / "answer.txt"
        answer_path.write_text(run.get("text", ""))
        (output / "result.json").write_text(json.dumps(run, indent=2) + "\n")
        batch = run["batch"]
        client.download(batch["urls"]["results"], output / "results.jsonl")
        snapshot = client.json(batch["urls"]["snapshot"], "POST", {})
        end = time.monotonic() + 180
        while True:
            batch = client.json(batch["urls"]["status"])
            entry = next((s for s in batch["snapshots"] if s["id"] == snapshot["snapshot_id"]), None)
            if entry and entry["state"] == "ready":
                archive = client.download(entry["download_url"], output / "artifacts.zip")
                break
            if entry and entry["state"] == "failed":
                raise RuntimeError("Artifact ZIP failed: " + str(entry.get("error")))
            if time.monotonic() >= end:
                raise RuntimeError("Artifact ZIP is still preparing for run " + run_id)
            time.sleep(2)
        print(json.dumps({"run_id": run_id, "state": run["state"], "text_output": run.get("text", ""),
                          "text_file": str(answer_path), "zip_file": archive}, indent=2))
        return 0 if run["state"] == "succeeded" else 2
    except (OSError, ValueError, RuntimeError) as exc:
        print(str(exc), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
