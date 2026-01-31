import os
import pytest

from sqlalchemy import text

from src.db import get_engine
from src.tracer import TraceStore
from src import memory


@pytest.mark.skipif(
    not os.getenv("ORCH_DATABASE_URL", "").startswith("postgresql"),
    reason="Postgres integration test skipped (ORCH_DATABASE_URL not configured)",
)
def test_postgres_trace_and_memory_tables(tmp_path):
    engine = get_engine()
    assert engine is not None

    store = TraceStore(enabled=True)
    handle = store.start_trace({"route": "/test"})
    assert handle is not None

    store.record_step(handle.trace_id, "unit", {"status": "ok"})

    with engine.begin() as conn:
        traces = conn.execute(text("SELECT COUNT(*) FROM traces")).scalar_one()
        steps = conn.execute(text("SELECT COUNT(*) FROM trace_steps")).scalar_one()

    assert traces >= 1
    assert steps >= 1

    memory.capture_candidate_memory(
        user_id_hash="user123",
        conversation_id="conv1",
        text="remember this: postgres persistence works",
        trace_id=handle.trace_id,
    )

    with engine.begin() as conn:
        mem_count = conn.execute(text("SELECT COUNT(*) FROM memory_candidates")).scalar_one()

    assert mem_count >= 1
