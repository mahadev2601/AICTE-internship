"""
config.py — Centralised configuration for Fitness Buddy.

All environment variables are loaded here once. Every other module
imports from this file instead of calling os.getenv() directly.
"""

import os
from dotenv import load_dotenv

# Load .env from the project root
load_dotenv()

# ── IBM watsonx.ai credentials ────────────────────────────────────────────────
WATSONX_API_KEY: str = os.getenv("WATSONX_API_KEY", "")
WATSONX_URL: str     = os.getenv("WATSONX_URL", "https://us-south.ml.cloud.ibm.com")
WATSONX_PROJECT: str = os.getenv("WATSONX_PROJECT_ID", "")

# ── IBM Granite model ─────────────────────────────────────────────────────────
# granite-4-h-small uses the chat API (system/user messages)
MODEL_ID = "ibm/granite-4-h-small"

# Chat API params (max_tokens, not max_new_tokens)
MODEL_PARAMS: dict = {
    "max_tokens": 700,    # enough for detailed, structured responses
    "temperature": 0.3,   # low = more factual, consistent outputs
    "top_p": 0.85,
}

# ── Application constants ─────────────────────────────────────────────────────
APP_NAME    = "Fitness Buddy"
APP_VERSION = "2.1.0"

# ── Storage & Database ────────────────────────────────────────────────────────
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATABASE_PATH = os.getenv("DATABASE_PATH", os.path.join(BASE_DIR, "data", "fitness_buddy.db"))
PROFILES_FILE = os.path.join(os.getenv("PROFILES_DIR", BASE_DIR), "profiles.json")

# ── Context Window & Memory ───────────────────────────────────────────────────
MAX_CHAT_HISTORY_TURNS = int(os.getenv("MAX_CHAT_HISTORY_TURNS", "6"))
MAX_CONTEXT_TOKENS_APPROX = int(os.getenv("MAX_CONTEXT_TOKENS_APPROX", "1200"))
ENABLE_SAFETY_GUARDRAILS = os.getenv("ENABLE_SAFETY_GUARDRAILS", "true").lower() in ("true", "1", "yes")


def credentials_are_set() -> bool:
    """Return True only when both API key and project ID are non-empty."""
    return bool(WATSONX_API_KEY) and bool(WATSONX_PROJECT)

