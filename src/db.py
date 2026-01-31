from __future__ import annotations

import os
from typing import Optional

from sqlalchemy import create_engine
from sqlalchemy.engine import Engine

_ENGINE: Optional[Engine] = None


def get_engine() -> Optional[Engine]:
    """Return a shared SQLAlchemy engine if ORCH_DATABASE_URL is set."""
    global _ENGINE
    db_url = os.getenv("ORCH_DATABASE_URL", "").strip()
    if not db_url:
        return None
    if _ENGINE is None:
        _ENGINE = create_engine(
            db_url,
            pool_pre_ping=True,
            pool_recycle=int(os.getenv("ORCH_DB_POOL_RECYCLE", "300")),
            future=True,
        )
    return _ENGINE
