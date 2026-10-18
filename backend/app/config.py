"""Runtime configuration, read from environment variables."""

import os
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parent.parent

DATABASE_URL = os.environ.get(
    "CAREERFLOW_DATABASE_URL",
    f"sqlite:///{BACKEND_DIR / 'data' / 'careerflow.db'}",
)
