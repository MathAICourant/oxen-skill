# Yoke direct requests

Yoke sends a prompt directly to a model. Wagon runs an agent with computation
tools. Both web pages have **Direct requests** and **Batches** tabs, with separate
histories, activity, cancellation and downloads. API keys are created at
https://oxen.lemma.farm/keys; https://oxen.lemma.farm/ is the navigation menu.

For durable single model requests, use `https://oxen.lemma.farm/api/v1/yoke`.
Send the two Cloudflare headers and User-Agent documented in SKILL.md.

- `POST /run`: validate and queue one complete provider request.
- `GET /runs?offset=0&limit=50`: your direct request history, with `runs`, `total`,
  `offset`, `limit`. Maximum page size is 100. Uploaded JSONL batches are excluded.
- `GET /run/{run_id}`: state, final or partial answer in `text`, request JSON,
  usage, activity URL and saved-result/ZIP routes under `batch.urls`.
- `GET /run/{run_id}/activity?after=0&limit=100`: saved activity events and current
  streamed answer/reasoning. Reuse the byte `cursor` as `after` until `has_more`
  is false. Returned plaintext reasoning may be shown in a collapsed spoiler.
- `GET /run/{run_id}/activity.jsonl`: activity recorded so far.
- `POST /run/{run_id}/cancel`: cancel queued/running work. Provider work already
  accepted may still be billed.

Example POST body:

```json
{
  "endpoint": "/v1/responses",
  "timeout_seconds": 1200,
  "body": {
    "model": "gpt-6.2-sol",
    "input": "Factor x**8 - 1 over the rationals.",
    "reasoning": {"effort": "high"},
    "max_output_tokens": 8192,
    "stream": true
  }
}
```

`body` is the complete native request object for the selected endpoint.
`endpoint` defaults to `/v1/chat/completions`, with `/v1/responses`, `/v1/messages`
and `/v1/completions` also supported. `timeout_seconds` is 10–86400 and defaults
to 1200. A direct submission is limited to 4 MiB. Model-specific modifiers and
reasoning fields follow the same rules as the regular inference endpoints.
Validation sends no model calls; a valid direct request starts immediately.

The accepted response contains `run_id`, `batch_id`, `status_url`, `kind: "single"`
and a `batch` object with download URLs. The internal `batch_id` preserves the
existing results/ZIP preparation protocol; the request is listed under `/runs`
and stays out of the batch list. Intentional one-line JSONL uploads remain batches.

Direct Yoke requests share the same 15 model-call slots per provider with Yoke
batches and Wagon model calls. Standalone `/api/v1/responses` etc. calls do not use
this queue. Model calls are recorded against the submitting API key; browser
requests use the signed-in owner. Queued work persists; interrupted running
requests are not replayed automatically.

Use `batch.urls.results` to download JSONL at any time and POST to
`batch.urls.snapshot` to prepare a ZIP; poll `batch.urls.status` for the snapshot's
`download_url`. ZIPs contain request JSON, original response bytes, SSE events,
answer, returned reasoning and activity. Do not expose the private URLs or data
in public repositories. Every run, activity and download route checks ownership.

For JSONL uploads, the existing [Yoke batch API](batch-api.md) remains
`/api/v1/batch`; it lists uploaded batches, excluding direct requests.
