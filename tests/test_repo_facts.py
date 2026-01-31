import os
import re
import sqlite3
import importlib
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
        "- **Server routes**: `/health`, `/ready`, `/metrics`, `/echo`, `/v1/chat/completions`, `/v1/tools/execute`",
        "- **Default bind**: `ORCH_PORT=8088`, `ORCH_HOST=127.0.0.1`",
        "- **API flag**: `ORCH_ENABLE_API`",
        "- **Auth flags**: `ORCH_REQUIRE_BEARER`, `ORCH_BEARER_TOKEN`",
        "- **LLM flags**: `ORCH_LLM_ENABLED`, `ORCH_LLM_PROVIDER`, `ORCH_OLLAMA_URL`, `ORCH_MODEL_CHAT`, `ORCH_LLM_TIMEOUT_SEC`, `ORCH_LLM_HEALTH_TIMEOUT_SEC`",
        "- **Safety flags**: `ORCH_MAX_REQUEST_BYTES`, `ORCH_RATE_LIMIT_ENABLED`, `ORCH_RATE_LIMIT`, `ORCH_RATE_LIMIT_STORAGE_URL`, `ORCH_LOG_JSON`, `ORCH_LOG_LEVEL`, `ORCH_METRICS_ENABLED`",
        "- **Routing flags**: `ORCH_ORCHESTRATOR_MODE`, `ORCH_ROUTER_POLICY_PATH`",
        "- **DB flags**: `ORCH_DATABASE_URL`, `ORCH_DB_POOL_RECYCLE`",
        "- **Sandbox flags**: `ORCH_TOOL_SANDBOX_ENABLED`, `ORCH_TOOL_SANDBOX_REQUIRED`, `ORCH_SANDBOX_IMAGE`, `ORCH_SANDBOX_TIMEOUT_SEC`, `ORCH_SANDBOX_MEMORY_MB`, `ORCH_SANDBOX_CPU`, `ORCH_SANDBOX_TOOL_DIR`",
        "- **OTel flags**: `ORCH_OTEL_ENABLED`, `ORCH_OTEL_EXPORTER_OTLP_ENDPOINT`, `ORCH_SERVICE_NAME`",
        "- **Trace flags**: `ORCH_TRACE_ENABLED`, `ORCH_TRACE_DB_PATH`",
        "- **Memory flags**: `ORCH_MEMORY_ENABLED`, `ORCH_MEMORY_CAPTURE_ENABLED`, `ORCH_MEMORY_WRITE_POLICY`, `ORCH_MEMORY_CAPTURE_TTL_MINUTES`, `ORCH_MEMORY_DB_PATH`",
        "- **SQLite tables**: `traces`, `trace_steps`, `memory_candidates`",
        "- **Memory decision taxonomy**: `allow:explicit_intent`, `allow:dedupe_update`, `allow:capture_only`, `deny:feature_disabled`, `deny:policy_write_disabled`, `deny:no_explicit_intent`, `deny:scrubbed_too_short`, `deny:sensitive_content`, `deny:error`",
        "- **Toy example**: `examples/toy_orchestrator.py` uses `eval()` and includes `WARNING: eval() is dangerous - toy example only!`",
        "- **Non-goals**: not a hosted service; not a turnkey agent; no autonomous multi-agent planning in core (policy routing is deterministic)",
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
    from src import server
    importlib.reload(server)

    with server.app.test_client() as client:
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


def test_repo_facts_tables_exist(tmp_path: Path):
    from src.tracer import TraceStore
    from src import memory

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


def test_toy_example_contains_eval_warning():
    toy_path = Path(__file__).resolve().parents[1] / "examples" / "toy_orchestrator.py"
    content = toy_path.read_text()

    assert "WARNING: eval() is dangerous - toy example only!" in content
