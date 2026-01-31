import os
import warnings

import pytest

os.environ.setdefault("ORCH_RATE_LIMIT_STORAGE_URL", "memory://")

warnings.filterwarnings(
    "ignore",
    message=r"Using the in-memory storage for tracking rate limits.*",
    category=UserWarning,
)


@pytest.fixture(autouse=True)
def _block_network_when_requested(monkeypatch):
    if os.getenv("NO_NETWORK", "0") != "1":
        yield
        return

    import socket

    def _blocked(*_args, **_kwargs):
        raise RuntimeError("Network access blocked by NO_NETWORK=1")

    monkeypatch.setattr(socket, "socket", _blocked)
    monkeypatch.setattr(socket, "create_connection", _blocked)
    yield
