# Codex and Claude Code clients

Get a 90-day API key from https://oxen.lemma.farm/. Store its client ID in
`CF_ACCESS_CLIENT_ID` and secret in `CF_ACCESS_CLIENT_SECRET`. Both headers are
required; a provider SDK's `api_key` alone does not authenticate to Oxen.

## Codex

Use a recent Codex CLI. Add this to `~/.codex/config.toml`:

```toml
model_provider = "oxen"
model_reasoning_effort = "high"
# Optional starting selection: model = "gpt-6.2-sol"

[features]
api_key_model_discovery = true

[model_providers.oxen]
name = "Oxen"
base_url = "https://oxen.lemma.farm/api/v1"
model_catalog_url = "https://oxen.lemma.farm/api/v1/codex/models"
env_key = "CF_ACCESS_CLIENT_SECRET"
wire_api = "responses"
requires_openai_auth = false
supports_websockets = true

[model_providers.oxen.env_http_headers]
CF-Access-Client-Id = "CF_ACCESS_CLIENT_ID"
CF-Access-Client-Secret = "CF_ACCESS_CLIENT_SECRET"
```

Run `codex`, then `/model` to select a model and effort. Oxen's native Codex
catalog intersects the live model registry with known Codex coding metadata.
Only supported effort levels are included. Other provider models remain in
`GET /api/v1/models`; that OpenAI-shaped catalog is not a substitute for the
Codex-native catalog. Current GPT-6.2 aliases allow low/medium/high/xhigh/max.

## Claude Code

```bash
export ANTHROPIC_BASE_URL="https://oxen.lemma.farm/api"
export ANTHROPIC_API_KEY="YOUR_API_KEY"  # SDK placeholder
export ANTHROPIC_CUSTOM_HEADERS="CF-Access-Client-Id: ${CF_ACCESS_CLIENT_ID}
CF-Access-Client-Secret: ${CF_ACCESS_CLIENT_SECRET}"
export CLAUDE_CODE_ENABLE_GATEWAY_MODEL_DISCOVERY=1
export CLAUDE_CODE_EFFORT_LEVEL=high
claude
# In Claude Code: /model
# Optional starting selection: claude --model claude-sonnet-4-6
```

The base URL ends at `/api`; the Anthropic client adds `/v1`. Keep the placeholder
`ANTHROPIC_API_KEY` even when custom headers authenticate: discovery requires a
built-in credential setting. Claude Code fetches `/v1/models` on startup and
filters for Claude/Anthropic model IDs. Restart the client to refresh its cache.
Exact effort choices depend on model capabilities and client version.

References: [Codex provider settings](https://github.com/openai/codex/blob/main/codex-rs/model-provider-info/src/lib.rs),
[Claude Code discovery](https://code.claude.com/docs/en/llm-gateway-protocol#model-discovery).
