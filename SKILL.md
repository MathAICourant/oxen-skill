---
name: oxen-skill
description: Send model requests through Oxen, choose model-specific parameters, validate and submit JSONL batches to Wagon, monitor progress, cancel requests, and retrieve full or partial results.
---

# Oxen

Use the authenticated Oxen model API at `https://oxen.lemma.farm/api/v1`.
The user obtains a 90-day service credential at `https://oxen.lemma.farm/`.
Send both headers on every API request, including WebSocket upgrades:

- `CF-Access-Client-Id`: read from `CF_ACCESS_CLIENT_ID`.
- `CF-Access-Client-Secret`: read from `CF_ACCESS_CLIENT_SECRET`.

Read credentials from the user's environment or secret store. Do not print them,
commit them, put them in URLs, or include them in result archives. No provider
API key is needed. Some SDKs require a placeholder `api_key`; the Cloudflare
headers perform authentication. Browser cookies do not replace service credentials.

For a public model reference without browser login, read
[references/models.md](references/models.md) for common aliases and their primary
parameter documentation.

## Single model requests

Consult the signed-in [Oxen docs](https://oxen.lemma.farm/docs) for the current
model catalog and each model's **Parameters & limits** references. Request
`GET /models` with the service headers for the current registered IDs. A model
being listed does not guarantee its upstream is available.

- Responses: `POST /responses`, set `reasoning: {"effort":"high"}`; SSE uses
  `stream:true`. WebSocket mode uses `wss://oxen.lemma.farm/api/v1/responses`,
  `response.create` events and an array-valued `input`.
- Chat Completions: `POST /chat/completions`, use `messages` and
  `reasoning_effort:"high"`. Optional fields depend on the model and provider.
- Anthropic Messages: `POST /messages`, use `max_tokens` and either adaptive
  `thinking` plus `output_config.effort`, or a supported manual token budget.

Effort names, output caps, structured-output fields and sampling controls differ
by model and endpoint. Preserve the user's selected model and settings; do not
silently substitute a different model. Use stateless requests with explicit
conversation history when crossing provider adapters. Provider-specific SDK
`extra_body` fields become top-level HTTP JSON keys.

## Wagon batches

The web UI is `https://oxen.lemma.farm/wagon`. The service API is
`https://oxen.lemma.farm/api/v1/batch`. Batches and downloads are private to the
credential owner's verified email. This skill repository is public; do not put
user inputs or outputs in it.

Each nonblank JSONL line is a complete request body. Select a default endpoint
for the file, or use the documented per-line envelope for mixed endpoints.
Read [references/batch-api.md](references/batch-api.md) for exact routes, schemas,
state transitions, timestamps, cancellation and downloads.

The included standard-library helper handles chunked uploads and polling:

```bash
python3 scripts/oxen_batch.py validate requests.jsonl --endpoint /v1/chat/completions
python3 scripts/oxen_batch.py submit BATCH_ID
python3 scripts/oxen_batch.py status BATCH_ID
python3 scripts/oxen_batch.py download BATCH_ID --output ./results --zip
python3 scripts/oxen_batch.py cancel BATCH_ID
```

Validation sends no model requests. The whole file must pass before submission.
If asked only to validate, stop at `ready` and report the `batch_id` and any errors.
If the user has requested execution, submit after successful validation without
inventing an additional confirmation step. Never submit an invalid batch.

Wagon shares a maximum of 15 active requests per provider across all batches.
OpenRouter models share one provider pool; Flatiron models share another.
Each request is independent; file order does not create a conversation or pass
one answer into another request.

Poll status at a reasonable interval, such as 5 seconds. Report counts and the
submission/estimated-completion/actual-completion timestamps. Estimates are
approximate, using provider history and queue position, with an initial
60-second duration assumption. A completed batch can contain failed or cancelled
requests: inspect the individual states before claiming success.

JSONL results are downloadable during execution. ZIP preparation is asynchronous;
poll the batch's `snapshots` entries until `ready`, then use its `download_url`.
Snapshots preserve original input, expanded request JSON, response bytes, SSE
intermediates and partial text as saved. Treat running results as partial.

Cancellation closes the local upstream connection; the provider may still finish
or bill work already accepted. Queued requests resume after a worker restart;
active interrupted requests are not automatically replayed. Retry failed or
interrupted work only when requested, using a new batch containing those records.
Do not re-submit an entire batch merely because a status or download request failed.
