"""Shared OpenAI client helper for modules that choose to import it."""

from __future__ import annotations

import os

from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()


def get_openai_client() -> OpenAI:
    """Return OpenAI client configured from OPENAI_API_KEY environment variable."""
    api_key = os.getenv("OPENAI_API_KEY", "")
    if not api_key:
        raise RuntimeError("OPENAI_API_KEY is not configured")
    return OpenAI(api_key=api_key)
