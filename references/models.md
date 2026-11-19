# Model parameters and modifiers

Reference reviewed 2026-11-19. Query authenticated `GET /api/v1/capabilities` for current IDs, efforts, limits and parameter references, or `GET /api/v1/models` for just IDs. The complete dated [model-capabilities.json](model-capabilities.json) snapshot is available publicly without browser login. Gateway declarations and native provider APIs can differ; links below do not guarantee every native field is forwarded.

## gpt-6.2-sol

Reasoning efforts: low, medium, high, xhigh, max.

API references describe the native OpenAI API; the Codex-account gateway can normalize or omit fields. For GPT-6.2 omit temperature, top_p and logprob controls; use Responses for tool calling.

- [All Responses parameters](https://developers.openai.com/api/reference/python/resources/responses/methods/create)
- [All Chat parameters](https://developers.openai.com/api/reference/python/resources/chat/subresources/completions/methods/create)
- [Model specs](https://developers.openai.com/api/docs/models/gpt-6.2-sol)

## gpt-6.2-astra

Reasoning efforts: low, medium, high, xhigh, max.

API references describe the native OpenAI API; the Codex-account gateway can normalize or omit fields. For GPT-6.2 omit temperature, top_p and logprob controls; use Responses for tool calling.

- [All Responses parameters](https://developers.openai.com/api/reference/python/resources/responses/methods/create)
- [All Chat parameters](https://developers.openai.com/api/reference/python/resources/chat/subresources/completions/methods/create)
- [Model specs](https://developers.openai.com/api/docs/models/gpt-6.2-astra)

## claude-sonnet-4-6

Reasoning efforts: low, medium, high, max.

Use max_tokens, stream, tools/tool_choice and thinking/output_config for Messages. Sampling controls vary by Claude model and thinking mode; consult its model specs.

- [All Messages parameters](https://platform.claude.com/docs/en/api/messages/create)
- [Claude model specs](https://platform.claude.com/docs/en/models/overview)
- [Thinking & effort](https://platform.claude.com/docs/en/build-with-claude/effort)

## claude-opus-5-5

Reasoning efforts: low, medium, high, xhigh, max.

Use max_tokens, stream, tools/tool_choice and thinking/output_config for Messages. Sampling controls vary by Claude model and thinking mode; consult its model specs.

- [All Messages parameters](https://platform.claude.com/docs/en/api/messages/create)
- [Claude model specs](https://platform.claude.com/docs/en/models/overview)
- [Thinking & effort](https://platform.claude.com/docs/en/build-with-claude/effort)

## glm-5.3

Reasoning efforts: low, high, max.

Parameters below are advertised by OpenRouter for this exact model. Some entries are capability flags, not literal request fields. Oxen translates endpoint formats; check the referenced schema for each option.

- [Model parameters & limits](https://openrouter.ai/z-ai/glm-5.3)
- [All OpenRouter parameters](https://openrouter.ai/docs/api_reference/parameters)

## deepseek-4.1

Reasoning efforts: none, low, high, max.

Parameters below are advertised by OpenRouter for this exact model. Some entries are capability flags, not literal request fields. Oxen translates endpoint formats; check the referenced schema for each option.

- [Model parameters & limits](https://openrouter.ai/deepseek/deepseek-v4.1-flash-1017)
- [All OpenRouter parameters](https://openrouter.ai/docs/api_reference/parameters)
- [Native DeepSeek parameter reference](https://api-docs.deepseek.com/api/create-chat-completion/)

## kimi-k3

Reasoning efforts: not verified; omit effort.

Flatiron runs vLLM behind LiteLLM. Use the vLLM API/sampling references plus the model card; LiteLLM and Oxen must also forward a field for it to take effect. Its model list does not publish deployment-specific parameter support.

- [Model card & generation settings](https://huggingface.co/moonshotai/Kimi-K3)
- [Chat request format](https://developers.openai.com/api/reference/python/resources/chat/subresources/completions/methods/create)
- [vLLM OpenAI-compatible API & extra parameters](https://docs.vllm.ai/en/latest/serving/online_serving/openai_compatible_server/)
- [All vLLM sampling parameters](https://docs.vllm.ai/en/latest/api/vllm/sampling_params/)
- [LiteLLM vLLM forwarding](https://docs.litellm.ai/docs/providers/vllm)
- [LiteLLM request parameters](https://docs.litellm.ai/docs/completion/input)

## mimo-v2.6-pro

Reasoning efforts: not verified; omit effort.

Flatiron runs vLLM behind LiteLLM. Use the vLLM API/sampling references plus the model card; LiteLLM and Oxen must also forward a field for it to take effect. Its model list does not publish deployment-specific parameter support.

- [Model card & generation settings](https://huggingface.co/XiaomiMiMo/MiMo-V2.6-Pro-MOPD)
- [Chat request format](https://developers.openai.com/api/reference/python/resources/chat/subresources/completions/methods/create)
- [vLLM OpenAI-compatible API & extra parameters](https://docs.vllm.ai/en/latest/serving/online_serving/openai_compatible_server/)
- [All vLLM sampling parameters](https://docs.vllm.ai/en/latest/api/vllm/sampling_params/)
- [LiteLLM vLLM forwarding](https://docs.litellm.ai/docs/providers/vllm)
- [LiteLLM request parameters](https://docs.litellm.ai/docs/completion/input)

## mistral-medium-3.5

Reasoning efforts: not verified; omit effort.

Flatiron runs vLLM behind LiteLLM. Use the vLLM API/sampling references plus the model card; LiteLLM and Oxen must also forward a field for it to take effect. Its model list does not publish deployment-specific parameter support.

- [Model card & generation settings](https://huggingface.co/mistralai/Mistral-Medium-3.5-128B)
- [Chat request format](https://developers.openai.com/api/reference/python/resources/chat/subresources/completions/methods/create)
- [Native Mistral parameters (deployment may differ)](https://docs.mistral.ai/api/endpoint/chat)
- [vLLM OpenAI-compatible API & extra parameters](https://docs.vllm.ai/en/latest/serving/online_serving/openai_compatible_server/)
- [All vLLM sampling parameters](https://docs.vllm.ai/en/latest/api/vllm/sampling_params/)
- [LiteLLM vLLM forwarding](https://docs.litellm.ai/docs/providers/vllm)
- [LiteLLM request parameters](https://docs.litellm.ai/docs/completion/input)

## qwen3.8-27b

Reasoning efforts: not verified; omit effort.

Flatiron runs vLLM behind LiteLLM. Use the vLLM API/sampling references plus the model card; LiteLLM and Oxen must also forward a field for it to take effect. Its model list does not publish deployment-specific parameter support.

- [Model card & generation settings](https://huggingface.co/Qwen/Qwen3.8-27B-FP8)
- [Chat request format](https://developers.openai.com/api/reference/python/resources/chat/subresources/completions/methods/create)
- [vLLM OpenAI-compatible API & extra parameters](https://docs.vllm.ai/en/latest/serving/online_serving/openai_compatible_server/)
- [All vLLM sampling parameters](https://docs.vllm.ai/en/latest/api/vllm/sampling_params/)
- [LiteLLM vLLM forwarding](https://docs.litellm.ai/docs/providers/vllm)
- [LiteLLM request parameters](https://docs.litellm.ai/docs/completion/input)
