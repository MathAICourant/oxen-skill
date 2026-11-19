# Wagon ephemeral agents

Wagon runs each question in a new private Daytona sandbox, with Harbor selecting
and running the agent. Users need only their existing Oxen credential. Yoke at
`/api/v1/batch` is the separate queue for direct model requests without tools.

Use `https://oxen.lemma.farm/api/v1/wagon` as the API root. Send the two Cloudflare
service headers documented in SKILL.md, plus `User-Agent: oxen-skill/1.0`.
Do not give provider or Daytona keys to clients. Outputs belong to the credential
owner's verified email. Model calls are charged to the exact submitting API key's
usage ledger; browser-created runs belong to the signed-in account.

## Discovery and one question

- `GET /catalog`: approved software environments, pinned snapshot/source hashes,
  available agents, worker and provider-call limits. Treat this as authoritative.
- `GET /schema`: the versioned request JSON Schema.
- `GET /runs?offset=0&limit=50`: your individual questions, separately from
  uploaded JSONL batches. Returns `runs`, `total`, `offset`, `limit`; each run
  includes its ID, question preview, agent/model, state, timestamps, activity
  URL and a browser `page_url`. The maximum page size is 100.
- `POST /run`: one question plus settings; validates before immediately queuing
  execution. Returns `run_id`, `batch_id`, `status_url`, and batch/download URLs.
- `GET /run/{run_id}`: status, answer in `text`, resolved request, usage,
  execution metadata, cleanup outcome and the containing batch's download URLs.
- `GET /run/{run_id}/activity?after=0&limit=100`: paginated activity JSON. Reuse
  the returned byte `cursor` as `after`; keep fetching while `has_more`. Events
  include `at`, `kind`, `title`, `text`; the response also includes run state,
  usage, final answer if available, workspace file metadata and cleanup state.
- `GET /run/{run_id}/activity.jsonl`: download activity recorded so far.
- `GET /run/{run_id}/files?path=calculation.py`: bounded UTF-8 preview of a
  collected workspace file. Use paths marked `preview_available` in activity.
- `POST /run/{run_id}/cancel`: cancel queued/running work; collect what is available
  and remove its sandbox. Provider work already accepted can still be billed.

The web interface has matching **Direct requests** and **Batches** tabs on
Wagon and Yoke. Agent/environment/resource controls are specific to Wagon;
model endpoint/request controls are specific to Yoke. Both retain the selected
activity view, per-request timestamps, cancellation, results and ZIP downloads.

Single-question submissions are persisted with `kind: "single"`; intentional
JSONL uploads have `kind: "batch"`, even for a one-line file. `/batch` lists only
uploaded batches; `/runs` lists individual questions. Existing single questions
are migrated into that collection without rerunning them or changing saved files.
The `batch_id` and download URLs on a single-run response are retained for API
compatibility and artifact preparation; they do not make it appear in the batch
list.

The enabled agents are:

| Agent | Models | Model API |
| --- | --- | --- |
| `terminus-2` | Oxen text models | Chat Completions |
| `codex` | OpenAI models | Responses |
| `claude-code` | Claude models | Anthropic Messages |

IFM's `k2-horizon` is available with Terminus-2 and `reasoning_effort: "high"`.
Wagon preserves the provider-returned reasoning fields required for IFM history
replay, including an empty returned trace; it does not generate missing reasoning.

Codex 0.170.0 and Claude Code 2.1.318 were tested with real SymPy computations,
code/answer artifacts, per-key accounting and sandbox deletion. Claude Code effort choices are low/medium/high/xhigh/max where supported by the
selected model; none/minimal are not native Claude Code effort settings.
The catalog
reports enabled choices and the native runtime versions/checksums; consult it
rather than assuming all upstream agents are installed. Codex runtime bundles
include its code-mode host and companion files, not only the main executable.

Native agents use a credential-free localhost endpoint inside the sandbox. A
host worker forwards those requests over Daytona's authenticated control channel
to the metered Oxen gateway. Provider credentials, Daytona keys and the user's
Cloudflare secret are not installed in the sandbox. Native streaming responses
are currently buffered per model call before being delivered to the CLI.

The initial `math-python-v1` environment has Python 3.12.13, SymPy, mpmath, NumPy,
SciPy, matplotlib, pandas, NetworkX, Git, ripgrep, curl, tmux, SQLite and C/C++ build
tools. Python dependencies and base image digest are pinned. Runs do not share
workspaces, mounted homes or previous agent history. The reusable snapshot contains
software only. Sandbox networks are disabled by default; the host-side agent
accesses model APIs through the metered Oxen relay.

```python
import os
import time
import requests

base = "https://oxen.lemma.farm/api/v1/wagon"
headers = {
    "CF-Access-Client-Id": os.environ["CF_ACCESS_CLIENT_ID"],
    "CF-Access-Client-Secret": os.environ["CF_ACCESS_CLIENT_SECRET"],
    "User-Agent": "oxen-skill/1.0",
}
response = requests.post(base + "/run", headers=headers, timeout=30, json={
    "question": "Use SymPy to integrate x**4 from 0 to 1. Save the code.",
    "model": "deepseek-4.1",
    "reasoning_effort": "none",
    "environment": "math-python-v1",
    "resources": {"cpu": 2, "memory_gib": 4, "disk_gib": 10},
    "timeouts": {"run_seconds": 600},
})
response.raise_for_status()
run_id = response.json()["run_id"]
while True:
    response = requests.get(base + "/run/" + run_id, headers=headers, timeout=30)
    response.raise_for_status()
    run = response.json()
    if run["state"] not in ("queued", "running"):
        break
    time.sleep(5)
print(run.get("text", ""))
# Inspect run["state"], run.get("error"), and run.get("cleanup") as well.
# run["batch"]["urls"] contains results and ZIP snapshot preparation routes.
```

## Input files without sandbox internet

Set `download_urls` to an array of public HTTP(S) file URLs. Oxen downloads the
files on the server when the run starts, then copies them into the fresh sandbox
under `/workspace/inputs/`. The agent receives the file paths in its instructions.
This works with the default `network.mode: "none"`; it does not grant internet
access to the sandbox. Available through `POST /run`, every Wagon JSONL row, and
the browser's **Download URLs** field (one URL per line).

```json
{
  "question": "Inspect the paper provided in /workspace/inputs/ and save your notes.",
  "agent": "codex",
  "model": "gpt-6.2-sol",
  "download_urls": ["https://arxiv.org/pdf/1706.03762"],
  "network": {"mode": "none"}
}
```

Use the repeatable CLI flag for multiple files:

```bash
python3 scripts/oxen_wagon.py "Inspect the supplied paper and abstract" --agent codex --download-url https://arxiv.org/pdf/1706.03762 --download-url https://arxiv.org/abs/1706.03762
```

Names have a numeric prefix, for example `001-1706.03762.pdf`; each input has a
distinct name. `/workspace/inputs/manifest.json` maps original/final URLs to paths,
byte sizes, content types, download timestamps and SHA-256 hashes. The run status
includes `download_manifest`; the artifact ZIP preserves the original downloads
and manifest, as well as any files the agent changes. URLs can serve different
bytes over time, so compare the saved hashes when reproducing a run.

Limits: up to 10 distinct URLs, 64 MiB per file and 128 MiB combined; the combined
size is also bounded by `limits.max_artifact_bytes`. Each file has at most 60
seconds, within the run's setup budget. Increase `timeouts.setup_seconds` for
several slow inputs. Redirects are followed up to five times. Only public
destinations on ports 80/443 are accepted; credentials in URLs, private/internal
addresses and redirects to them are rejected. No Oxen/provider credentials are
sent to download sites. Use public URLs without embedded secrets. Archives are
copied as files and are not automatically extracted; PDF-reading packages are
not guaranteed to be present in the software preset.

Validation checks URL syntax without fetching anything. Downloads occur only
after submission; any failed download fails the run before the agent starts.
Completed inputs remain downloadable in a ZIP snapshot if a later input fails.
The agent cannot fetch arbitrary new URLs mid-run with this setting.

Daytona currently rejects custom internet policies on the configured accounts;
`network.mode: "public"`/`"allowlist"` require an account tier that supports them.
Use `download_urls` with `network.mode: "none"` for pre-supplied web files.

## Live activity

The web Activity view polls about every two seconds. The selected run is saved
in the page URL (`/wagon?run=RUN_ID`) and restored after reload. Scrolling up
pauses following; recheck **Follow latest output** to resume. Terminal control
codes are removed in the display while Unicode is preserved; original terminal
logs remain in the artifact ZIP. Commands, completed tool
output, assistant messages and small text file previews appear as available.
Provider-returned reasoning or summaries are displayed in collapsed spoilers.
Encrypted/redacted reasoning is never decoded or reconstructed. Native model
responses are buffered per call, so this is not a token-by-token stream. Activity
is saved after completion and included in the artifact ZIP.

Live previews include up to 12 small text/code files (64 KiB each), from a
workspace listing capped at 200 files and two directory levels. Final artifacts
remain in the ZIP. The activity log is capped at 16 MiB and reports `truncated`
when that cap is reached. Every activity/preview/download route checks ownership.

`timeouts.run_seconds` is the **maximum agent execution time**, not a delay.
Agents stop earlier when finished. Setup, model-call, auxiliary-command and
cleanup deadlines are separate. A JSONL row’s `timeouts.run_seconds` overrides
the batch runtime setting.

## JSONL batch format

For one question, the standard-library CLI waits and returns `text_output` and
`zip_file`, also saving the answer, result metadata, JSONL and ZIP locally:

```bash
python3 scripts/oxen_wagon.py "Integrate x**4 from 0 to 1 with SymPy" --model deepseek-4.1 --effort none --cpu 2 --memory-gib 4 --max-runtime 600
python3 scripts/oxen_wagon.py "Check the integral with SymPy" --agent codex --model gpt-6.2-sol --effort low
python3 scripts/oxen_wagon.py "Check the integral with SymPy" --agent claude-code --model claude-sonnet-4-6 --effort low
```

Use `--question-file` to read the positional argument as a text file, `--no-wait`
to return the IDs immediately, and `--help` for the other resource and runtime flags.

Each nonblank line is a complete Wagon request object, not a Chat Completions
request. See the machine-readable
[JSON Schema](agent-request.schema.json). The whole file must validate before
submission starts any sandbox or model work. Omitted settings are expanded into
explicit defaults, saved as request JSON for each row. No credentials go in JSONL.

```jsonl
{"schema_version":1,"custom_id":"integral-1","question":"Use SymPy to integrate x**4 from 0 to 1. Save the code.","agent":"terminus-2","model":"deepseek-4.1","reasoning_effort":"none","environment":"math-python-v1","resources":{"cpu":2,"memory_gib":4,"disk_gib":10},"timeouts":{"setup_seconds":300,"run_seconds":600,"llm_seconds":180,"command_seconds":60,"cleanup_seconds":60},"limits":{"max_steps":40,"max_model_calls":80,"max_output_tokens":8192,"max_artifact_bytes":268435456},"daytona":{"auto_stop_minutes":5,"auto_delete_minutes":0,"ttl_minutes":22},"network":{"mode":"none","allowed_hosts":[]},"model_parameters":{}}
{"custom_id":"factor-1","question":"Factor x**8 - 1 over the rationals and verify the product using Python.","model":"gpt-6.2-sol","reasoning_effort":"high","timeouts":{"run_seconds":1200},"limits":{"max_steps":60}}
```

| Field | Default and meaning |
| --- | --- |
| `schema_version` | `1`; reject unknown versions. |
| `custom_id` | Optional user identifier, up to 512 characters. |
| `question` | Required task text, up to 1,000,000 characters. |
| `download_urls` | `[]`; up to 10 public HTTP(S) URLs fetched before execution and copied into `/workspace/inputs/`. See input-file limits and manifest above. |
| `agent` | `terminus-2`; must be enabled in `/catalog`. |
| `model` | `gpt-6.2-sol`, or `claude-sonnet-4-6` when `agent` is `claude-code`; must be in the live Oxen model catalog. |
| `reasoning_effort` | Omitted means model default. Values depend on model: `none`, `minimal`, `low`, `medium`, `high`, `xhigh`, `max`. Consult [models](models.md). |
| `environment` | `math-python-v1`; approved versioned preset from `/catalog`. |
| `resources.cpu` | `2` virtual CPUs; integer 1–8, subject to account/provider limits. |
| `resources.memory_gib` | `4` GiB RAM; integer 1–32. |
| `resources.disk_gib` | `10` GiB ephemeral disk including software; integer 10–100. |
| `timeouts.setup_seconds` | `300` seconds for each of sandbox creation and agent setup; 30–1200. |
| `timeouts.run_seconds` | `600` seconds for agent execution, including model calls and computation; 10–86400. Batch `timeout_seconds` supplies this default when the row omits it. |
| `timeouts.llm_seconds` | `180` seconds for each model request after acquiring a provider slot; 10–1200. |
| `timeouts.command_seconds` | `60` seconds for an individual sandbox exec RPC; 1–600. Processes started in the persistent terminal can continue beyond an RPC; the run deadline bounds the whole sandbox. A native CLI invocation itself uses the agent run deadline. |
| `timeouts.cleanup_seconds` | `60` seconds of cleanup grace; 15–300. A separately bounded reaper can run afterward. |
| `limits.max_steps` | `40` agent turns; 1–1000. Claude Code uses its native turn limit; Codex conservatively caps model HTTP requests, including retries. |
| `limits.max_model_calls` | `80` HTTP attempts, including retries/summarization; 1–2000. |
| `limits.max_output_tokens` | `8192` requested output tokens per call; 64–131072 and model-specific limits also apply. |
| `limits.max_artifact_bytes` | `268435456` (256 MiB) for one saved workspace export; 1 MiB–1 GiB. |
| `daytona.region` | Omitted uses the configured Daytona/account region. A snapshot must be usable there. |
| `daytona.auto_stop_minutes` | `5` minutes idle safety net; 1–60. Harbor keeps active jobs alive. |
| `daytona.auto_delete_minutes` | Always `0`: delete on stopping. Keeping/reusing a user's dirty sandbox is not supported. |
| `daytona.ttl_minutes` | Calculated as at least `ceil((2*setup_seconds + run_seconds + cleanup_seconds + 60)/60)`, minimum 5. An explicit shorter TTL is rejected. Harbor rearms this safety net during active ownership; the worker enforces the execution deadline. |
| `network.mode` | `none`, or `public`, or `allowlist`; unavailable provider policies fail without a permissive fallback. |
| `network.allowed_hosts` | Required nonempty only for `allowlist`; exact hostnames, supported wildcard hostnames, IPs or IP CIDRs; no URLs. |
| `model_parameters` | Optional `temperature`, `top_p`, `seed`, `frequency_penalty`, `presence_penalty`. Model-specific support still applies. A seed does not guarantee deterministic agent execution. |

Resource changes are applied to the sandbox and the observed resources are
recorded. If Daytona rejects them, the run fails rather than silently using
different resources. Daytona snapshots have fixed resource allocations. Wagon
caches a software-identical snapshot profile for requested CPU/RAM/disk values,
so it also works when live resizing is unavailable for the organization.
Pinning software and saving settings helps reproduce the
setup; model behavior and provider availability can change.

Batch root: `/api/v1/wagon/batch`. It has the same upload, validate, submit,
status, cancellation, request listing, `results.jsonl`, and asynchronous ZIP
snapshot protocol as the [Yoke batch API](batch-api.md); replace its API root.
Use `timeout_seconds:600` for Wagon's usual default. The `endpoint` batch setting
is accepted for helper compatibility; Wagon rows use the agent format above.

```bash
python3 scripts/oxen_batch.py --base https://oxen.lemma.farm/api/v1/wagon/batch validate questions.jsonl --timeout-seconds 600
python3 scripts/oxen_batch.py --base https://oxen.lemma.farm/api/v1/wagon/batch submit BATCH_ID
python3 scripts/oxen_batch.py --base https://oxen.lemma.farm/api/v1/wagon/batch status BATCH_ID
python3 scripts/oxen_batch.py --base https://oxen.lemma.farm/api/v1/wagon/batch download BATCH_ID --output ./results --zip
```

## Saved results and isolation

Result JSONL includes row/run identifiers, submitted/expected-completion/actual
completion dates, status/error, final answer, resolved request defaults, observed
CPU/RAM/disk, snapshot/source hash, Harbor/Daytona/LiteLLM versions, model call
counts and token usage, and sandbox cleanup outcome. ZIP snapshots also contain
the original input, per-row source/resolved requests, model request/response
records, Harbor trajectories and terminal output, and collected workspace files.
Only model-visible messages and outputs provided by the agent/provider can be
saved; do not promise access to private model reasoning.

Intermediate downloads contain what Oxen has saved so far. Live model calls and
logs can be present before the sandbox workspace export has completed. Failed,
cancelled and timed-out runs retain available intermediate data. A cleanup failure
is reported explicitly; do not claim a sandbox was removed unless recorded.
Cancellation returns promptly; `cleanup_pending` is true while cleanup continues.

The configured server cap is 15 active agent sandboxes. Actual model calls share
15 slots per provider with Yoke, including aliases sharing OpenRouter/Flatiron.
Direct standalone model API requests are outside this queue limit. Queued agent
work resumes after restart; interrupted active runs are not automatically replayed.
Keep Harbor internal: its native server does not provide Oxen's per-owner job
isolation. Never publish a user's inputs, outputs, credentials, or private runtime
configuration in this public skill repository.

## Server-managed Daytona account fallback

Oxen may switch to a configured backup Daytona account if sandbox provisioning
reports insufficient credits. The account alias is saved in `execution.json`
as `daytona_account`; the credential is never installed in the sandbox or
returned in results. Cleanup uses the recorded account. This is provisioning
failover, not live migration of an agent already running. Authentication,
permission, quota and network errors are reported rather than triggering
credit failover. Users do not need to select accounts or provide Daytona keys.
