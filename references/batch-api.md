# Wagon batch API

Base: `https://oxen.lemma.farm/api/v1/batch`. Authenticate every call with
`CF-Access-Client-Id` and `CF-Access-Client-Secret`. All JSON mutations use
`Content-Type: application/json`; raw input upload uses `application/octet-stream`.

## Create, upload, validate, submit

1. `POST /batch` relative to `/api/v1`, JSON:

   ```json
   {"filename":"requests.jsonl","endpoint":"/v1/chat/completions","timeout_seconds":1200}
   ```

   Returns HTTP 201 with `batch_id`, `state:"uploading"`, `counts`, timestamps
   and `urls` for status, upload, validation, submission, cancellation and downloads.
   The request timeout is an integer from 10 through 86,400 seconds.

2. `PUT /batch/{batch_id}/input?offset=0` with raw JSONL bytes. Upload at most
   4 MiB per call, advancing by the returned `next_offset`. Files may be up to
   2 GiB; individual request lines may be up to 4 MiB. Retrying the same bytes at
   the same offset is idempotent; conflicting bytes or an offset beyond the saved
   input return HTTP 409. Use `upload_bytes` from status to resume an upload of
   the same original file. Do not upload different content into an existing batch.

3. `POST /batch/{batch_id}/validate` with `{}`. Returns HTTP 202; poll status until
   `ready` or `invalid`. Validation checks all nonblank lines. It checks syntax,
   duplicate keys/non-finite numbers, endpoint shape and current text-model IDs;
   it does not guarantee every vendor-specific modifier will be accepted.
   Fix invalid files and create a new batch. No model requests execute here.

4. `POST /batch/{batch_id}/submit` with `{}` after `ready`. Returns HTTP 202.
   Submitting before validation succeeds, or submitting again, returns HTTP 409.
   If the response is lost, query status before doing anything else. Do not create
   another batch to compensate for an ambiguous submission response.

Supported default endpoints: `/v1/chat/completions`, `/v1/responses`,
`/v1/messages`, `/v1/completions`. Only POST text requests are supported.
Image/video/audio generation, arbitrary URLs and WebSocket requests are not
Wagon input formats. Use `stream:true` in a request body to preserve SSE events.

Complete request objects, one per physical line:

```jsonl
{"model":"deepseek-4.1","messages":[{"role":"user","content":"Factor x**8 - 1."}],"reasoning_effort":"high","max_tokens":4096}
{"model":"glm-5.3","messages":[{"role":"user","content":"Differentiate x**3."}],"reasoning_effort":"low","stream":true}
```

Optional envelope for a per-record endpoint and caller correlation:

```jsonl
{"custom_id":"problem-1","method":"POST","url":"/v1/responses","body":{"model":"gpt-6.2-sol","input":"Factor x**8 - 1.","reasoning":{"effort":"high"},"stream":true}}
```

Envelope fields are limited to `custom_id`, `method`, `url`, `body`.
`custom_id` is optional, at most 512 characters; the original line number is always
recorded as `ordinal`. Identical inputs/custom IDs remain separate requests.

## Status and request data

| Method/path relative to `/api/v1` | Behavior |
| --- | --- |
| `GET /batch` | Latest 100 batches owned by this user |
| `GET /batch/{id}` | Batch state, counts, timestamps, download links and snapshots |
| `GET /batch/{id}/requests?offset=0&limit=50` | Ordered request metadata; limit ≤200; optional `state=failed` etc. |
| `GET /batch/{id}/requests/{job_id}` | Saved response/partial text, error and original request body |
| `POST /batch/{id}/cancel` | Cancel the batch and its queued/active requests |
| `POST /batch/{id}/requests/{job_id}/cancel` | Cancel one queued/active request |
| `GET /batch/{id}/input` | Original JSONL, including an incomplete upload if still uploading |
| `GET /batch/{id}/results.jsonl` | Current per-line records, including queued/running/terminal states |
| `POST /batch/{id}/snapshots` | Prepare an as-is ZIP asynchronously; returns HTTP 202 and snapshot ID |
| `GET /batch/{id}/snapshots/{snapshot_id}/download` | Download a ready ZIP |

Always use the URLs returned by the service. A ZIP URL appears in the batch's
`snapshots[].download_url` once ready; poll `GET /batch/{id}`. Snapshot creation
can be slow for long files; it does not block model workers or require keeping
one HTTP request open. Files in a snapshot are captured as observed during
archiving, rather than as an atomic transaction across all active response files.

Batch states: `uploading`, `validating`, `invalid`, `ready`, `submitted`, `running`,
`completed`, `cancelled`. Request states: `queued`, `running`, `succeeded`, `failed`,
`cancelled`, `interrupted`, `invalid`. Batch completion means no queued/active work
remains, not that every request succeeded. Never automatically retry model calls.

A status response includes:

- `batch_id`, `state`, `filename`, `endpoint`, `timeout`.
- `created_at`, `submitted_at`, `expected_completed_at`, `completed_at`, `updated_at`.
- `total`, `invalid`, `upload_bytes`, `validated_bytes`, `error`.
- `counts`: all request states, plus aggregate input/output token counts.
- `provider_limit`, `estimate_note`, `snapshots`, `urls`.

Request metadata includes `id`, `ordinal`, optional `custom_id`, `model`, `provider`,
`endpoint`, `state`, `submitted_at`, `started_at`, `expected_completed_at`,
`finished_at`, HTTP status, error and reported token usage. Submission/estimate
fields are null before submission; actual completion is null until finished.

Use status after any uncertain network result. JSONL current-state downloads and
ZIP snapshots can be taken before completion without cancelling work. JSONL
contains saved request metadata and response/text when available; the ZIP also
contains `input.jsonl`, `manifest.json`, `requests.jsonl` and per-line directories
with `source.json`, `request.json`, `response.body`, optional `events.jsonl`,
`answer.txt` and `result.json`. Missing files mean that phase had not produced data.

## Ordinary inference references

For single requests use `/api/v1/models`, `/api/v1/responses`,
`/api/v1/chat/completions` or `/api/v1/messages`, with the same credential headers.
The signed-in Oxen docs at `https://oxen.lemma.farm/docs` contain current aliases,
effort settings, endpoint differences and per-model modifier references.
OpenRouter and Flatiron requests cross adapters; their native documentation does
not imply every field is preserved. Flatiron uses vLLM behind LiteLLM.
