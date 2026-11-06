"""
agent/model.py — IBM watsonx.ai model initialisation and safe inference wrapper.

Uses IBM Granite (ibm/granite-4-h-small) via the chat API for
instruction-following responses. Falls back gracefully to curated
offline responses when credentials are missing or the API fails.
"""

from __future__ import annotations

import logging
import warnings
from typing import Optional

from config import (
    WATSONX_API_KEY,
    WATSONX_URL,
    WATSONX_PROJECT,
    MODEL_ID,
    MODEL_PARAMS,
    credentials_are_set,
)

logger = logging.getLogger(__name__)

# Lazy import — avoids ImportError when package is absent in offline mode
_ModelInference = None
_Credentials    = None


def _ensure_imports() -> bool:
    """Import ibm_watsonx_ai lazily. Return True on success."""
    global _ModelInference, _Credentials
    if _ModelInference is not None:
        return True
    try:
        from ibm_watsonx_ai import Credentials
        from ibm_watsonx_ai.foundation_models import ModelInference
        _Credentials    = Credentials
        _ModelInference = ModelInference
        return True
    except ImportError:
        logger.warning("ibm_watsonx_ai not installed — running in offline mode.")
        return False


def init_model() -> Optional[object]:
    """
    Initialise and return a ModelInference instance for IBM Granite.
    Returns None if credentials are missing or connection fails.
    """
    if not credentials_are_set():
        logger.info("Credentials not set — offline mode active.")
        return None
    if not _ensure_imports():
        return None
    try:
        credentials = _Credentials(url=WATSONX_URL, api_key=WATSONX_API_KEY)
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            model = _ModelInference(
                model_id=MODEL_ID,
                credentials=credentials,
                project_id=WATSONX_PROJECT,
            )
        logger.info("IBM Granite model '%s' initialised successfully.", MODEL_ID)
        return model
    except Exception as exc:
        logger.warning("Could not connect to watsonx.ai: %s — offline mode.", exc)
        return None


def generate(model: Optional[object], system: str, user: str, fallback: str) -> str:
    """
    Call model.chat() with a system + user message pair.

    - Uses the chat API which IBM Granite is optimised for.
    - Returns the assistant's reply stripped of whitespace.
    - Falls back to `fallback` on any exception or when model is None.
    - Never raises — the agent remains stable regardless of API state.
    """
    if model is None:
        return fallback
    messages = [
        {"role": "system", "content": system},
        {"role": "user",   "content": user},
    ]
    try:
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            response = model.chat(messages=messages, params=MODEL_PARAMS)  # type: ignore[union-attr]
        text = response["choices"][0]["message"]["content"].strip()
        return text if text else fallback
    except Exception as exc:
        logger.warning("chat() failed: %s", exc)
        return fallback
