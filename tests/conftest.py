import os
import warnings

os.environ.setdefault("ORCH_RATE_LIMIT_STORAGE_URL", "memory://")

warnings.filterwarnings(
    "ignore",
    message=r"Using the in-memory storage for tracking rate limits.*",
    category=UserWarning,
)
