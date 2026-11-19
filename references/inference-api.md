# Inference without browser access

This reference and the rest of oxen-skill are public. Agents do not need to open
Oxen's Cloudflare-protected HTML pages. Use the public skill for instructions and
the authenticated JSON API for live information and work.

## Authentication and discovery

Base URL: `https://oxen.lemma.farm/api/v1`. On **every** request, including status,
download and WebSocket upgrade requests, send:

```text
CF-Access-Client-Id: value of CF_ACCESS_CLIENT_ID
CF-Access-Client-Secret: value of CF_ACCESS_CLIENT_SECRET
User-Agent: oxen-skill/1.0
```

JSON POST requests also use `Content-Type: application/json`. The two Cloudflare
fields together are the Oxen API key. A provider API key is not needed. Some SDKs
require a nonempty placeholder `api_key`, while the headers perform authentication.
The user obtains credentials from `/keys`; agents receive them through an
environment or secret store. Never print, commit or include them in ZIP artifacts.

- `GET /capabilities`: current model IDs, provider, endpoint families, supported
  reasoning efforts, budgets, context/output limits, notes and public links for
  model-specific modifiers. Includes `gateway_version` and `reviewed` metadata.
  Missing or empty declarations mean unverified support, not arbitrary support.
- `GET /models`: simpler OpenAI-compatible `data[].id` inventory.
- `GET /codex/models`: Codex-native model picker metadata; use only for Codex
  gateway discovery as explained in [client-config.md](client-config.md).
- `GET /wagon/catalog`: enabled agents, native runtime versions/checksums,
  environments/software snapshots and worker/provider limits.
- `GET /wagon/schema`: current complete agent request schema. An offline copy is
  [agent-request.schema.json](agent-request.schema.json).

The dated [model-capabilities.json](model-capabilities.json) contains the full
catalog snapshot publicly. Prefer `/capabilities` for live decisions. A model
listed by the gateway can still be unavailable upstream; retain the requested
model and report failures rather than silently substituting one.

## Choose the execution path

| Task | API | Reference |
| --- | --- | --- |
| Immediate model response | `/responses`, `/chat/completions`, `/messages` | Below |
| Saved model request, live partial text, downloads | `/yoke/run` | [direct-api.md](direct-api.md) |
| JSONL of independent model request bodies | `/batch` | [batch-api.md](batch-api.md) |
| Coding agent with Python/tools and saved files | `/wagon/run` | [agent-api.md](agent-api.md) |
| JSONL of independent coding-agent questions | `/wagon/batch` | [agent-api.md](agent-api.md) |

Yoke and Wagon single submissions return `run_id` and `status_url`; poll status
and inspect errors, usage and downloads. A returned `batch_id` supports the common
artifact protocol and does not put a direct request in the batch list. Intentional
one-line JSONL uploads remain batches. Every line/run has independent context;
pass conversation history explicitly when wanted.

## Endpoint and effort fields

Paths below are relative to the base URL.

| Endpoint | Required prompt shape | Output cap | Reasoning |
| --- | --- | --- | --- |
| `POST /responses` | `model`, `input` (string or array) | `max_output_tokens` | `reasoning: {"effort":"high"}` |
| `POST /chat/completions` | `model`, `messages` | `max_completion_tokens` or `max_tokens`, model-dependent | `reasoning_effort:"high"` |
| `POST /messages` | `model`, `messages`, `max_tokens` | `max_tokens` | Adaptive `thinking` + `output_config.effort`, or manual budget |
| `POST /completions` | `model`, `prompt` | `max_tokens` | Prefer the modern endpoints for effort controls |

Use only an effort listed for the selected model in `/capabilities`. The gateway
recognizes none/minimal/low/medium/high/xhigh/max/auto across models, but no model
supports every value. Omission uses the provider default; it differs from `none`.
`auto` is not a universal effort, and this gateway does not declare `ultra`.

For Messages, `adaptive:true` models use `thinking:{"type":"adaptive"}` and a
supported `output_config.effort`. Budget models use
`thinking:{"type":"enabled","budget_tokens":4096}` without `output_config`.
Respect `budget_min`, `budget_max` and `disable_allowed`; keep the total
`max_tokens` above the thinking budget. Output caps also cover reasoning, so a
small cap can leave little room for the visible answer. Do not send conflicting
model suffixes, budgets and effort fields.

OpenAI GPT-6.2 aliases currently declare low/medium/high/xhigh/max: omit
`temperature`, `top_p` and logprob controls and prefer Responses for tool calling.
GLM 5.3 declares low/high/max and always reasons. DeepSeek 4.1 declares
none/low/high/max through this gateway. Flatiron/vLLM model effort levels are
unverified when the capability entry has no levels; omit the field then.

`k2-horizon` uses IFM K2 Horizon; `high` is its only effective effort. Prefer
Chat Completions for provider-native controls. See [models.md](models.md) for
required reasoning replay and recommended sampling defaults. Wagon supports it
with Terminus-2.

HTTP inference responses include `X-Oxen-Usage-Id`; retain it when reporting an
issue so operators can correlate the call with private central gateway logs and
the usage ledger. WebSocket handshakes have `X-Oxen-Connection-Id`. These IDs
do not grant access to another user's logs or artifacts. Gateway content logs
rotate; use saved Yoke/Wagon requests for durable research outputs.

## Python examples

Install `openai` for the first example. Replace the two placeholders with the
user's credentials, or read them from environment variables as in SKILL.md.

```python
from openai import OpenAI

client = OpenAI(
    base_url="https://oxen.lemma.farm/api/v1",
    api_key="YOUR_API_KEY",  # SDK placeholder; the headers authenticate.
    default_headers={
        "CF-Access-Client-Id": "YOUR_CLIENT_ID",
        "CF-Access-Client-Secret": "YOUR_API_KEY",
        "User-Agent": "oxen-skill/1.0",
    },
)
response = client.responses.create(
    model="gpt-6.2-sol",
    input="Factor x**8 - 1 over the rationals.",
    reasoning={"effort": "high"},
    store=False,
)
print(response.output_text)

response = client.chat.completions.create(
    model="deepseek-4.1",
    messages=[{"role": "user", "content": "Factor x**8 - 1."}],
    reasoning_effort="high",
    max_tokens=8192,
)
print(response.choices[0].message.content)
```

For native Anthropic Messages, install `anthropic` and use the API root without
`/v1` because the SDK adds that part:

```python
from anthropic import Anthropic

client = Anthropic(
    base_url="https://oxen.lemma.farm/api",
    api_key="YOUR_API_KEY",
    default_headers={
        "CF-Access-Client-Id": "YOUR_CLIENT_ID",
        "CF-Access-Client-Secret": "YOUR_API_KEY",
        "User-Agent": "oxen-skill/1.0",
    },
)
response = client.messages.create(
    model="claude-sonnet-4-6",
    max_tokens=8192,
    messages=[{"role": "user", "content": "Factor x**8 - 1."}],
    thinking={"type": "adaptive"},
    output_config={"effort": "high"},
)
for block in response.content:
    if block.type == "text":
        print(block.text)
```

## Streaming and request modifiers

Set `stream:true` for SSE on text POST endpoints. For Responses, concatenate
`response.output_text.delta` events and read until `response.completed` or a
failure/incomplete event. For Chat Completions, concatenate
`choices[].delta.content`; request `stream_options:{"include_usage":true}` for a
final usage chunk. Messages streams use `content_block_delta.delta.text` for
answer text. Only show reasoning text or summaries explicitly returned by the
provider; encrypted or redacted content is unavailable.

For Responses WebSockets, connect to
`wss://oxen.lemma.farm/api/v1/responses` with both Cloudflare headers, then send
`{"type":"response.create","model":"MODEL_ID","input":[{"role":"user","content":"Question"}],"reasoning":{"effort":"high"}}`.
WebSocket `input` must be an array. Each turn is accounted separately.

Common optional fields include `temperature`, `top_p`, stop sequences, tools and
`tool_choice`, structured-output formats, seed, and provider-specific sampling
controls. They are not universally supported. Responses uses `text.format` for
structured output; Chat Completions uses `response_format`. SDK `extra_body`
keys become top-level request JSON. Consult each capability entry's `references`
for the provider's complete public schema and its `modifier_note` for gateway
limits. No authenticated website visit is needed to use those references.

OpenRouter and Flatiron requests cross format adapters. Flatiron uses vLLM behind
LiteLLM; native vLLM parameters must also survive LiteLLM and Oxen forwarding.
Use stateless Responses inputs and supply history instead of relying on stored
response IDs across adapters. Model limits are gateway declarations, not a
promise of upstream account entitlement or that every modifier has been tested.
Image/audio/video/realtime routes may be registered but are not validated by the
text/agent workflows; do not put those requests in the text queues.

## Limits, status, errors and downloads

Wagon allows 15 active sandboxes total. Yoke direct requests, Yoke batches and
Wagon model calls share 15 simultaneous calls per provider. GLM/DeepSeek share
OpenRouter's pool; Flatiron models share theirs. Sandbox computation can proceed
without occupying a model-call slot. Standalone immediate inference calls are
outside that durable queue limit.

- `401`/`403`, HTML login pages or Access redirects: check both service headers,
  credential expiry/revocation and the API Access policy. Browser login does not
  replace API authentication.
- `400`: inspect the request shape, endpoint, model, effort and token/budget
  settings. Keep the provider's error context when reporting it.
- `404`: check the exact versioned path and returned owner-scoped URL. A missing
  run can also mean it belongs to another verified owner.
- `409`: query current batch state; validation must finish before submission and
  repeated submission is rejected. Upload retries must use the same bytes/offset.
- `429`: respect `Retry-After` and provider limits. Do not replay an entire batch
  because one request or status call failed.
- Timeouts/network failures: retry read-only polling with backoff. After an
  ambiguous submission, query history/status before resubmitting work.

Run states are queued/running/succeeded/failed/cancelled/interrupted. Batch states
also include uploading/validating/invalid/ready/submitted/completed. Batch
completion is not per-line success: inspect individual states. Queued jobs
survive restarts; interrupted active requests are not automatically replayed.
Cancellation can leave billable provider work already accepted.

Results and download URLs need the same service headers. Use returned URLs rather
than inventing paths; do not follow cross-origin redirects with credentials.
JSONL and ZIP snapshots can be downloaded before completion, as partial state.
ZIP preparation is asynchronous: POST the snapshot URL, then poll the status URL
until `snapshots[].state` is `ready` and download that entry's `download_url`.
Wagon cancellation can return `cleanup_pending` while bounded cleanup finishes.
Save the model, effort, complete request/defaults, gateway version, timestamps,
usage, final text, raw response and artifact ZIP for reproducibility.
