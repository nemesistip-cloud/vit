# VIT AI: Current Runtime Boundaries

This document describes the code paths present in this repository. It does not certify external deployment health, trained-model quality, or provider availability.

## Request paths

- **Shared gateway:** `AIGateway` routes chat and prediction requests through the configured `vit-ai` client. The client contract in this repository uses `/health`, `/api/v1/chat`, and `/api/v1/models`. Remote health was not reachable during the latest investigation, so the upstream runtime and its model artifacts remain unverified.
- **Local prediction fallback:** If the remote route fails, the gateway may use the local orchestrator only for prediction intent and only with supplied structured match evidence. It does not invent default odds. The orchestrator currently requires provider market odds for its prediction path. Conversational requests are reported unavailable rather than answered with prediction output.
- **Conversational provider fallback:** `call_ai_with_provider` tries Gemini and AIMLAPI only after the primary gateway reports a fallback, and never uses those providers to replace a prediction response. Provider status exposes configuration separately from connectivity; configured keys do not mean a provider was probed or is ready.
- **Application assistant:** `/api/ai/assistant/chat` serves database-backed responses for supported prediction/evaluation queries, and labels their data source. It explicitly declines requests for live chain, wallet, financial, or administrative data that are not connected to this chat. The platform assistant has separate authenticated routes and permission-scoped integration services.
- **VITPredict:** The football forecasting baseline is statistical. The Qwen material in `QWEN_AI_INTEGRATION.md` is a proposal, not an implemented or evaluated prediction model. LLM-generated text must not be presented as a verified forecast or as evidence of predictive accuracy.

## Model and evaluation reporting

The local orchestrator's model list distinguishes callable wrappers from loaded model artifacts. A callable wrapper is not evidence that trained weights are loaded. Model accuracy is reported as unmeasured until derived from verified evaluation data; the model's configured ensemble weight is not an accuracy estimate.

Prediction analytics should include only verified outcomes and exclude demo, synthetic, live-generated, and seeded records. Report sample size, accuracy, multiclass Brier score, and log loss together. An empty evaluation set is unavailable evidence, not zero accuracy.

## Degradation and operations

- AI is optional: gateway errors and absent providers should not block core wallet, authentication, or network APIs.
- Prediction fallback is limited to supplied structured evidence. When that evidence or the inference service is unavailable, callers receive an explicit unavailable response.
- Gemini and AIMLAPI are optional configured fallbacks; no live connectivity is assumed by status reporting.
- Validate upstream health, startup behavior, and runtime model availability in the deployment environment before describing them as operational. Do not infer deployment status from a route existing in this repository.

## Verification status

The focused backend regression suites passed (36 tests). Frontend type-check and production build passed, and browser checks for the assistant and VITPredict states passed. The full browser suite passed 28 of 33 tests; five unrelated existing checks failed on match detail, verification, home status, subscription error selectors, and genesis workspace behavior. Public `vit-ai` and gateway health probes timed out; no production inference or deployed-browser verification is claimed.

## Operational configuration

The remote `vit-ai` service URL and authentication settings are read by `VitAIClient`. `GEMINI_API_KEY` (or `GOOGLE_API_KEY`) and `AIMLAPI_API_KEY` are optional fallback credentials. Keep values in the approved secret store; status endpoints should report only whether each provider is configured, not return credentials.
