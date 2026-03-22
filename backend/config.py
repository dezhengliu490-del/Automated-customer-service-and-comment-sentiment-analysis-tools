"""Load environment and shared settings for the backend."""

from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv

_ENV_PATH = Path(__file__).resolve().parent / ".env"
load_dotenv(_ENV_PATH)


def get_gemini_api_key() -> str:
    key = os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")
    if not key or not key.strip():
        raise RuntimeError(
            "Missing API key: set GEMINI_API_KEY or GOOGLE_API_KEY in the environment "
            "or in backend/.env (see backend/.env.example)."
        )
    return key.strip()


def get_gemini_model() -> str:
    return os.environ.get("GEMINI_MODEL", "gemini-2.0-flash").strip()
