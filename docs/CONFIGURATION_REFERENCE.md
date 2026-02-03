# Configuration Reference (ORCH_*)

Single-source, auto-scannable reference of Orchestrators-v2 environment flags.

| Variable | Default | Description | Risk Level |
| --- | --- | --- | --- |
| ORCH_AGENT_DIR | config/agents (repo) | Directory for agent YAML definitions. | Low |
| ORCH_AGENT_PROMPT_ALLOW_OVERBUDGET | 0 | Allow over-budget agent prompts globally. | Med |
| ORCH_BEARER_TOKEN | "" | Bearer token required when auth is enabled. | High |
| ORCH_DATABASE_URL | "" | SQLAlchemy database URL for shared engine. | High |
| ORCH_DB_POOL_RECYCLE | 300 | SQLAlchemy pool recycle seconds. | Low |
| ORCH_ENABLE_API | 1 | Enable API routes. | High |
| ORCH_ENV | development | Environment mode (development/production). | Med |
| ORCH_HOST | 127.0.0.1 | HTTP bind host. | Low |
| ORCH_INTENT_CACHE_DB_PATH | instance/intent_cache.db | SQLite path for intent cache. | Low |
| ORCH_INTENT_CACHE_ENABLED | 1 | Enable intent cache. | Low |
| ORCH_INTENT_CACHE_TTL_SEC | 600 | Intent cache TTL seconds. | Low |
| ORCH_INTENT_DECISION_EXPOSE | 0 | Expose intent decisions in responses. | Med |
| ORCH_INTENT_HITL_DB_PATH | instance/intent_hitl.db | HITL queue database path. | Med |
| ORCH_INTENT_HITL_ENABLED | 1 | Enable human-in-the-loop queue. | Med |
| ORCH_INTENT_MIN_CONFIDENCE | 0.85 | Minimum intent confidence for routing. | Med |
| ORCH_INTENT_MIN_GAP | 0.05 | Minimum confidence gap between top intents. | Med |
| ORCH_INTENT_ROUTER_ENABLED | 0 | Enable intent router. | Med |
| ORCH_INTENT_ROUTER_SHADOW | 0 | Shadow intent routing comparisons. | Low |
| ORCH_LLM_ENABLED | 0 | Enable LLM calls. | High |
| ORCH_LLM_NETWORK_ENABLED | 0 | Allow outbound provider calls. | High |
| ORCH_LLM_HEALTH_TIMEOUT_SEC | 5 | LLM health check timeout (seconds). | Low |
| ORCH_LLM_MAX_OUTPUT_CHARS | 4000 | Max output size for provider responses. | High |
| ORCH_LLM_PROVIDER | ollama | LLM provider backend. | Med |
| ORCH_LLM_RETRY_COUNT | 0 | Provider retry count. | Med |
| ORCH_LLM_RETRY_BACKOFF_SEC | 0.5 | Backoff between retries (seconds). | Low |
| ORCH_LLM_CIRCUIT_MAX_FAILURES | 3 | Circuit breaker failure threshold. | High |
| ORCH_LLM_CIRCUIT_RESET_SEC | 30 | Circuit breaker reset window (seconds). | Med |
| ORCH_LLM_MODEL_ALLOWLIST | "" | Approved provider model IDs. | Med |
| ORCH_LLM_TIMEOUT_SEC | 30 | LLM inference timeout (seconds). | Med |
| ORCH_LOG_JSON | 1 | Emit JSON logs. | Low |
| ORCH_LOG_LEVEL | INFO | Log level. | Low |
| ORCH_MAX_REQUEST_BYTES | 1048576 | Max HTTP request size (bytes). | Med |
| ORCH_MAX_TOKENS | 16384 | Token budget for input context. | High |
| ORCH_MEMORY_CAPTURE_ENABLED | 0 | Enable memory capture pipeline. | High |
| ORCH_MEMORY_CAPTURE_TTL_MINUTES | 180 | TTL for memory candidates (minutes). | Med |
| ORCH_MEMORY_DB_PATH | instance/orchestrator_core.db | Memory database path. | Med |
| ORCH_MEMORY_ENABLED | 0 | Enable memory subsystem. | High |
| ORCH_MEMORY_MAX_CHARS | 500 | Max chars retained for memory capture. | Low |
| ORCH_MEMORY_SCRUB_REDACT_PII | 1 | Redact PII in memory writes. | High |
| ORCH_MEMORY_WRITE_POLICY | off | Memory write policy (off/strict/capture_only). | High |
| ORCH_METRICS_ENABLED | 1 | Enable Prometheus metrics endpoint. | Med |
| ORCH_OLLAMA_URL | http://127.0.0.1:11434 | Ollama base URL for LLM calls. | Med |
| ORCH_ORCHESTRATOR_MODE | basic | Orchestrator mode (basic/advanced). | Med |
| ORCH_OTEL_ENABLED | 0 | Enable OpenTelemetry tracing. | Med |
| ORCH_OTEL_EXPORTER_OTLP_ENDPOINT | http://127.0.0.1:4318/v1/traces | OTLP exporter endpoint. | Med |
| ORCH_POLICY_DECISIONS_IN_RESPONSE | 0 | Include policy decisions in API responses. | Med |
| ORCH_PORT | 8088 | HTTP bind port. | Low |
| ORCH_RATE_LIMIT | 60 per minute | Default rate limit. | Med |
| ORCH_RATE_LIMIT_ENABLED | 1 | Enable rate limiting. | Med |
| ORCH_RATE_LIMIT_STORAGE_URL | "" | Storage URL for rate limiter backend. | High |
| ORCH_REQUIRE_BEARER | 1 | Require Bearer auth (forced in production). | High |
| ORCH_ROUTER_POLICY_PATH | config/router_policy.yaml | Policy routing config path. | Med |
| ORCH_SANDBOX_CPU | 0.5 | Sandbox CPU quota. | Low |
| ORCH_SANDBOX_IMAGE | python:3.12-slim | Sandbox container image. | Med |
| ORCH_SANDBOX_MEMORY_MB | 256 | Sandbox memory limit (MB). | Low |
| ORCH_SANDBOX_TIMEOUT_SEC | 10 | Sandbox execution timeout (seconds). | Med |
| ORCH_SANDBOX_TOOL_DIR | sandbox_tools | Sandbox tool directory. | Low |
| ORCH_SEMANTIC_ROUTER_EMBED_MODEL | nomic-embed-text:latest | Embedding model for semantic router. | Med |
| ORCH_SEMANTIC_ROUTER_ENABLED | 0 | Enable semantic router. | Med |
| ORCH_SEMANTIC_ROUTER_MIN_SIMILARITY | 0.80 | Minimum similarity for semantic routing. | Med |
| ORCH_SEMANTIC_ROUTER_OLLAMA_URL | http://127.0.0.1:11434 | Ollama URL for semantic router embeddings. | Med |
| ORCH_SEMANTIC_ROUTER_TIMEOUT_SEC | 10 | Semantic router request timeout (seconds). | Low |
| ORCH_SERVICE_NAME | orchestrators-v2 | OTel service name. | Low |
| ORCH_SQLITE_WAL_ENABLED | 1 | Enable SQLite WAL mode. | Low |
| ORCH_TIER3_MIN_TOKENS | 32768 | Token threshold to force Tier 3 summary mode. | High |
| ORCH_TOKEN_BUDGET_SUMMARY_ENABLED | 0 | Enable summary insertion during pruning. | High |
| ORCH_TOKEN_SAFETY_MARGIN | 1.1 | Safety margin for byte fallback token counts. Lowering below 1.0 risks model-side context overflows. | Med |
| ORCH_TOKENIZER_DIR | ORCH_TOKENIZER/tokenizers | Tokenizer directory path. | Low |
| ORCH_TOKENIZER_MODEL | gpt-aimee | Tokenizer model name. | Low |
| ORCH_TOOL_OUTPUT_MAX_CHARS | 4000 | Max chars returned from tool output. | Med |
| ORCH_TOOL_OUTPUT_SCRUB_ENABLED | 1 | Scrub sensitive output from tools. | High |
| ORCH_TOOL_POLICY_ENFORCE | 0 | Enforce tool policy decisions. | High |
| ORCH_TOOL_POLICY_PATH | config/tool_policy.yaml | Tool policy config path. | Med |
| ORCH_TOOL_SANDBOX_ENABLED | 1 | Enable sandbox for tool execution. | High |
| ORCH_TOOL_SANDBOX_FALLBACK | 0 | Allow fallback when sandbox unavailable. | Med |
| ORCH_TOOL_SANDBOX_REQUIRED | 1 | Require sandbox for tool execution. | High |
| ORCH_TOOL_WEB_SEARCH_ENABLED | 0 | Enable web search tool. | Med |
| ORCH_TRUST_PANEL_ENABLED | 0 | Enable Trust Panel endpoints. | High |
| ORCH_TRUST_PANEL_DEBUG | 0 | Enable Trust Panel debug metadata. | Med |
| ORCH_TRUST_PANEL_MAX_EVENTS | 200 | Max events returned per query. | Med |
| ORCH_TRUST_PANEL_MAX_VALUE_CHARS | 500 | Max chars retained per payload value. | Med |
| ORCH_TRACE_DB_PATH | instance/trace.db | Trace DB path. | Med |
| ORCH_TRACE_ENABLED | 1 | Enable trace receipts. | High |
| ORCH_MODEL_CHAT | qwen2.5:3b | Chat model name. | Med |
| ORCH_MODEL_TOOL | qwen2.5:3b | Tool model name. | Med |
| ORCH_MODEL_REASONER | ORCH_MODEL_CHAT | Reasoner model name. | Med |
| ORCH_MODEL_CHAT_TIER1_MAX_TOKENS | 4096 | Tier 1 max tokens for chat model. | Med |
| ORCH_MODEL_REASONER_TIER1_MAX_TOKENS | 32768 | Tier 1 max tokens for reasoner model. | Med |

Risk Levels:
- Low: cosmetic or performance tuning.
- Med: affects routing, observability, or resource limits.
- High: affects security, compliance posture, or memory/tool safety.
