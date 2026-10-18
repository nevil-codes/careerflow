"""Runtime configuration, read from environment variables."""

import os
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parent.parent

DATABASE_URL = os.environ.get(
    "CAREERFLOW_DATABASE_URL",
    f"sqlite:///{BACKEND_DIR / 'data' / 'careerflow.db'}",
)

# Default Ollama endpoint for new provider configs. In Docker, point this at the host
# (http://host.docker.internal:11434) or at an `ollama` compose service.
OLLAMA_URL = os.environ.get("CAREERFLOW_OLLAMA_URL", "http://localhost:11434")

# Seconds to wait for one LLM response. Local models can be slow on first load.
LLM_TIMEOUT = float(os.environ.get("CAREERFLOW_LLM_TIMEOUT", "180"))
