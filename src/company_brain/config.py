"""
config.py — centralised configuration loaded from environment variables.

All modules import from here; nothing reads os.environ directly.
"""

import os
from pathlib import Path
from dotenv import load_dotenv, find_dotenv

# Load .env from project root or working directory
_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
env_file = _PROJECT_ROOT / ".env"
if env_file.exists():
    load_dotenv(env_file, override=True)
else:
    load_dotenv(find_dotenv(usecwd=True), override=True)


# ── HydraDB / Bolt ────────────────────────────────────────────────────────────
BOLT_URI: str = os.getenv("HYDRA_BOLT_URI", "bolt://127.0.0.1:7687")
HYDRA_USER: str = os.getenv("HYDRA_USER", "neo4j")
HYDRA_PASSWORD: str = os.getenv("HYDRA_PASSWORD", "local-development-token-32-bytes")

# ── LLM ───────────────────────────────────────────────────────────────────────
GEMINI_API_KEY: str = os.getenv("GEMINI_API_KEY", "")
# Model used for extraction and resolution adjudication.
GEMINI_MODEL: str = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")

# ── Data paths ────────────────────────────────────────────────────────────────
DATA_DIR: Path = _PROJECT_ROOT / "data"
RAW_DATA_DIR: Path = DATA_DIR / "raw"
QUESTIONS_DIR: Path = DATA_DIR / "questions"
QUESTIONS_FILE: Path = QUESTIONS_DIR / "questions.jsonl"
EXTRA_QUESTIONS_FILE: Path = QUESTIONS_DIR / "extra_questions.jsonl"

# ── Pipeline tuning ───────────────────────────────────────────────────────────
# Maximum number of hops for multi-hop traversal queries.
MAX_HOP_DEPTH: int = int(os.getenv("MAX_HOP_DEPTH", "4"))
# Batch size for UNWIND Cypher writes.
WRITE_BATCH_SIZE: int = int(os.getenv("WRITE_BATCH_SIZE", "500"))
# Minimum fuzzy similarity score (0-100) to form a blocking candidate pair.
BLOCKING_THRESHOLD: int = int(os.getenv("BLOCKING_THRESHOLD", "85"))
# Rate limiting & Retries for Gemini API
LLM_DELAY_SECONDS: float = float(os.getenv("LLM_DELAY_SECONDS", "1.0"))
LLM_MAX_RETRIES: int = int(os.getenv("LLM_MAX_RETRIES", "5"))
LLM_RETRY_BACKOFF: float = float(os.getenv("LLM_RETRY_BACKOFF", "2.0"))

def get_gemini_api_key() -> str:
    return os.getenv("GEMINI_API_KEY") or GEMINI_API_KEY

# ── Validation ────────────────────────────────────────────────────────────────
def validate() -> None:
    """Raise if critical config is missing."""
    key = get_gemini_api_key()
    if not key:
        raise EnvironmentError(
            "GEMINI_API_KEY is not set. Copy .env.example to .env and fill it in."
        )
