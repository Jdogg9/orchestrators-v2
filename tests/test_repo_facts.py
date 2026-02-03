import os
import re
import sqlite3
from pathlib import Path

import pytest


def _read_repo_facts_block(readme_path: Path) -> list[str]:
    content = readme_path.read_text()
    start_marker = "<!-- REPO_FACTS_START -->"
    end_marker = "<!-- REPO_FACTS_END -->"
    if start_marker not in content or end_marker not in content:
        raise AssertionError("Repo Facts block markers not found")

    block = content.split(start_marker, 1)[1].split(end_marker, 1)[0]
    lines = [line.strip() for line in block.strip().splitlines() if line.strip()]
    return lines


def _extract_backtick_tokens(line: str) -> list[str]:
    return re.findall(r"`([^`]+)`", line)


def test_repo_facts_block_matches_expected():
    readme_path = Path(__file__).resolve().parents[1] / "README.md"
    lines = _read_repo_facts_block(readme_path)

    expected_lines = [
        "- **Server routes**: `/health`, `/ready`, `/metrics`, `/echo`, `/v1/chat/completions`, `/v1/tools/execute`, `/v1/tools/approve`, `/v1/agents`, `/v1/agents/<name>`, `/v1/agents/<name>/chat`, `/v1/audit/verify`, `/v1/trust/events`, `/v1/trust/trace/<trace_id>`, `/v1/trust/verify/<trace_id>`",
        "- **Default bind**: `ORCH_PORT=8088`, `ORCH_HOST=127.0.0.1`",
        "- **Environment flag**: `ORCH_ENV`",
        "- **API flag**: `ORCH_ENABLE_API`",
        "- **Auth flags**: `ORCH_REQUIRE_BEARER`, `ORCH_BEARER_TOKEN`",
        "- **LLM flags**: `ORCH_LLM_ENABLED`, `ORCH_LLM_NETWORK_ENABLED`, `ORCH_LLM_PROVIDER`, `ORCH_OLLAMA_URL`, `ORCH_MODEL_CHAT`, `ORCH_LLM_TIMEOUT_SEC`, `ORCH_LLM_HEALTH_TIMEOUT_SEC`, `ORCH_LLM_MAX_OUTPUT_CHARS`, `ORCH_LLM_RETRY_COUNT`, `ORCH_LLM_RETRY_BACKOFF_SEC`, `ORCH_LLM_CIRCUIT_MAX_FAILURES`, `ORCH_LLM_CIRCUIT_RESET_SEC`, `ORCH_LLM_MODEL_ALLOWLIST`",
        "- **Safety flags**: `ORCH_MAX_REQUEST_BYTES`, `ORCH_RATE_LIMIT_ENABLED`, `ORCH_RATE_LIMIT`, `ORCH_RATE_LIMIT_STORAGE_URL`, `ORCH_LOG_JSON`, `ORCH_LOG_LEVEL`, `ORCH_METRICS_ENABLED`, `ORCH_TRUST_PANEL_ENABLED`, `ORCH_TRUST_PANEL_DEBUG`, `ORCH_TRUST_PANEL_MAX_EVENTS`, `ORCH_TRUST_PANEL_MAX_VALUE_CHARS`",
        "- **Routing flags**: `ORCH_ORCHESTRATOR_MODE`, `ORCH_ROUTER_POLICY_PATH`, `ORCH_INTENT_ROUTER_ENABLED`, `ORCH_INTENT_ROUTER_SHADOW`, `ORCH_INTENT_DECISION_EXPOSE`",
        "- **Semantic routing flags**: `ORCH_SEMANTIC_ROUTER_ENABLED`, `ORCH_SEMANTIC_ROUTER_MIN_SIMILARITY`, `ORCH_SEMANTIC_ROUTER_EMBED_MODEL`, `ORCH_SEMANTIC_ROUTER_OLLAMA_URL`, `ORCH_SEMANTIC_ROUTER_TIMEOUT_SEC`",
        "- **Intent routing flags**: `ORCH_INTENT_MIN_CONFIDENCE`, `ORCH_INTENT_MIN_GAP`, `ORCH_INTENT_CACHE_ENABLED`, `ORCH_INTENT_CACHE_DB_PATH`, `ORCH_INTENT_CACHE_TTL_SEC`, `ORCH_INTENT_HITL_ENABLED`, `ORCH_INTENT_HITL_DB_PATH`",
        "- **DB flags**: `ORCH_DATABASE_URL`, `ORCH_DB_POOL_RECYCLE`, `ORCH_SQLITE_WAL_ENABLED`",
        "- **Sandbox flags**: `ORCH_TOOL_SANDBOX_ENABLED`, `ORCH_TOOL_SANDBOX_REQUIRED`, `ORCH_TOOL_SANDBOX_FALLBACK`, `ORCH_SANDBOX_IMAGE`, `ORCH_SANDBOX_TIMEOUT_SEC`, `ORCH_SANDBOX_MEMORY_MB`, `ORCH_SANDBOX_CPU`, `ORCH_SANDBOX_TOOL_DIR`",
        "- **Tool policy flags**: `ORCH_TOOL_POLICY_ENFORCE`, `ORCH_TOOL_POLICY_PATH`",
        "- **Tool approval flags**: `ORCH_TOOL_APPROVAL_ENFORCE`, `ORCH_TOOL_APPROVAL_TTL_SEC`, `ORCH_TOOL_APPROVAL_DB_PATH`",
        "- **Tool feature flags**: `ORCH_TOOL_WEB_SEARCH_ENABLED`",
        "- **Tool output flags**: `ORCH_TOOL_OUTPUT_MAX_CHARS`, `ORCH_TOOL_OUTPUT_SCRUB_ENABLED`, `ORCH_POLICY_DECISIONS_IN_RESPONSE`",
        "- **OTel flags**: `ORCH_OTEL_ENABLED`, `ORCH_OTEL_EXPORTER_OTLP_ENDPOINT`, `ORCH_SERVICE_NAME`",
        "- **Trace flags**: `ORCH_TRACE_ENABLED`, `ORCH_TRACE_DB_PATH`",
        "- **Memory flags**: `ORCH_MEMORY_ENABLED`, `ORCH_MEMORY_CAPTURE_ENABLED`, `ORCH_MEMORY_WRITE_POLICY`, `ORCH_MEMORY_CAPTURE_TTL_MINUTES`, `ORCH_MEMORY_DB_PATH`, `ORCH_MEMORY_SCRUB_REDACT_PII`",
        "- **SQLite tables**: `traces`, `trace_steps`, `memory_candidates`, `intent_cache`, `hitl_queue`, `tool_approvals`",
        "- **Memory decision taxonomy**: `allow:explicit_intent`, `allow:dedupe_update`, `allow:capture_only`, `deny:feature_disabled`, `deny:policy_write_disabled`, `deny:no_explicit_intent`, `deny:scrubbed_too_short`, `deny:sensitive_content`, `deny:error`",
        "- **Toy example**: `examples/toy_orchestrator.py` uses an AST-safe evaluator (no `eval`).",
        "- **Non-goals**: not a cloud/SaaS platform; no autonomous multi-agent planning in core (policy routing is deterministic)",
    ]

    assert lines == expected_lines


def test_repo_facts_taxonomy_matches_memory_module():
    readme_path = Path(__file__).resolve().parents[1] / "README.md"
    lines = _read_repo_facts_block(readme_path)
    taxonomy_line = next(line for line in lines if line.startswith("- **Memory decision taxonomy**:"))
    readme_taxonomy = set(_extract_backtick_tokens(taxonomy_line))

    from src.memory import ALLOWED_DECISION_REASONS

    assert readme_taxonomy == set(ALLOWED_DECISION_REASONS)


def test_repo_facts_routes_match_server():
    os.environ["ORCH_REQUIRE_BEARER"] = "0"
    os.environ["ORCH_LLM_ENABLED"] = "0"
    os.environ["ORCH_ENABLE_API"] = "1"
    os.environ["ORCH_METRICS_ENABLED"] = "1"
    os.environ["ORCH_TRUST_PANEL_ENABLED"] = "1"
    from src.server import create_app
    app = create_app()

    with app.test_client() as client:
        health = client.get("/health")
        assert health.status_code == 200

        ready = client.get("/ready")
        assert ready.status_code == 200

        metrics = client.get("/metrics")
        assert metrics.status_code == 200

        echo = client.post("/echo", json={"message": "ok"})
        assert echo.status_code == 200

        chat = client.post(
            "/v1/chat/completions",
            json={"messages": [{"role": "user", "content": "hi"}]},
        )
        assert chat.status_code == 200

        tool_exec = client.post(
            "/v1/tools/execute",
            json={"name": "echo", "args": {"message": "hi"}},
        )
        assert tool_exec.status_code == 200

        audit = client.post(
            "/v1/audit/verify",
            json={},
        )
        assert audit.status_code == 400

        trust_events = client.get("/v1/trust/events")
        assert trust_events.status_code == 200


def test_repo_facts_tables_exist(tmp_path: Path):
    from src.tracer import TraceStore
    from src import memory
    from src.intent_cache import IntentCache
    from src.hitl_queue import HitlQueue

    trace_db = tmp_path / "trace.db"
    store = TraceStore(db_path=str(trace_db), enabled=True)
    assert trace_db.exists()

    with sqlite3.connect(trace_db) as conn:
        rows = conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()
        names = {row[0] for row in rows}

    assert {"traces", "trace_steps"}.issubset(names)

    mem_db = tmp_path / "orchestrator_core.db"
    with sqlite3.connect(mem_db) as conn:
        memory._ensure_memory_candidates_schema(conn)
        rows = conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()
        names = {row[0] for row in rows}

    assert "memory_candidates" in names

    intent_db = tmp_path / "intent_cache.db"
    IntentCache(db_path=str(intent_db), enabled=True)
    with sqlite3.connect(intent_db) as conn:
        rows = conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()
        names = {row[0] for row in rows}
    assert "intent_cache" in names

    hitl_db = tmp_path / "hitl_queue.db"
    HitlQueue(db_path=str(hitl_db), enabled=True)
    with sqlite3.connect(hitl_db) as conn:
        rows = conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()
        names = {row[0] for row in rows}
    assert "hitl_queue" in names

    approvals_db = tmp_path / "tool_approvals.db"
    from src.approval_store import ToolApprovalStore
    ToolApprovalStore(db_path=str(approvals_db))
    with sqlite3.connect(approvals_db) as conn:
        rows = conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()
        names = {row[0] for row in rows}
    assert "tool_approvals" in names


def test_toy_example_contains_eval_warning():
    toy_path = Path(__file__).resolve().parents[1] / "examples" / "toy_orchestrator.py"
    content = toy_path.read_text()

    assert "Safe math via AST-based evaluator (no eval)" in content
