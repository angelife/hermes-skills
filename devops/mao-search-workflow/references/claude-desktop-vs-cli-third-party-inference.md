# Claude Desktop vs Claude Code CLI — Third-Party Inference Restrictions

Verified facts from 2026-07 search session. Use as starting knowledge for future searches; still recheck sources before relying.

## Confirmed behavior
- Claude Desktop 1.6259.1 added client-side model name validation in Gateway mode.
- Desktop rejects model names that do not contain Anthropic-family markers such as `claude`, `sonnet`, `opus`, `haiku`, `anthropic`.
- Error shape seen in the wild: "expected a gateway model route referencing an Anthropic model" / "configured model ... is not an Anthropic model".
- Claude Code CLI can still accept custom/non-Anthropic model names through `ANTHROPIC_MODEL` / settings when the endpoint speaks Anthropic Messages.
- Desktop's `inferenceModels` must be the provider's exact model IDs, because it auto-discovers or validates against `/v1/models`.

## Where to look when diagnosing user reports
- GitHub issue search: anthropics/claude-code + model validation/3P/Gateway
- Vendor docs for `inferenceProvider`, `inferenceGatewayBaseUrl`, `inferenceGatewayApiKey`, `modelDiscoveryEnabled`, `inferenceModels`
- Provider model catalog: does it expose Anthropic-style IDs or only internal aliases like `auto`, `deepseek-v4`?

## Workaround categories reported
- Proxy-layer model name mapping to Anthropic-style IDs
- Using providers that already expose Anthropic-format model names
- Sticking with Claude Code CLI for custom/non-Anthropic third-party models

## Remaining unknowns
- Exact validation regex/function source in `app.asar` for latest Desktop build
- Whether future Desktop updates relax or harden this restriction
- Whether CC Switch/Ollama/FreeLLMAPI added stable mapping configs after 1.6259.1
