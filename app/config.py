"""
ResQ-Odisha Configuration & Multi-Provider AI Key Auto-Detection.
Supports Google Gemini, Groq, OpenAI, and Hugging Face tokens with seamless fallback.
"""

import os
from typing import Dict, Optional

# In-memory override for runtime updates
_ACTIVE_RUNTIME_KEY: Optional[str] = None

ENV_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".env")


def load_env_file() -> None:
    """Load key-value pairs from local .env file."""
    if os.path.exists(ENV_PATH):
        try:
            with open(ENV_PATH, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith("#") and "=" in line:
                        k, v = line.split("=", 1)
                        os.environ[k.strip()] = v.strip().strip('"').strip("'")
        except Exception:
            pass


load_env_file()


def detect_ai_provider(key: Optional[str]) -> str:
    """Auto-detect AI provider by API key prefix."""
    if not key:
        return "fallback"
    clean_key = key.strip()
    if clean_key.startswith("AIza"):
        return "gemini"
    elif clean_key.startswith("gsk_"):
        return "groq"
    elif clean_key.startswith("sk-"):
        return "openai"
    elif clean_key.startswith("hf_"):
        return "huggingface"
    return "gemini"


def get_ai_config() -> Dict[str, str]:
    """Retrieve active AI API key and resolved provider."""
    global _ACTIVE_RUNTIME_KEY
    raw_key = (
        _ACTIVE_RUNTIME_KEY
        or os.environ.get("AI_API_KEY")
        or os.environ.get("GEMINI_API_KEY")
        or os.environ.get("GROQ_API_KEY")
        or os.environ.get("OPENAI_API_KEY")
        or os.environ.get("HF_TOKEN")
        or ""
    ).strip()

    provider = detect_ai_provider(raw_key) if raw_key else "fallback"
    return {
        "api_key": raw_key,
        "provider": provider,
    }


def save_ai_key(key: str) -> Dict[str, str]:
    """Save API key to in-memory config and persist to .env file."""
    global _ACTIVE_RUNTIME_KEY
    clean_key = key.strip()
    _ACTIVE_RUNTIME_KEY = clean_key
    os.environ["AI_API_KEY"] = clean_key

    try:
        with open(ENV_PATH, "w", encoding="utf-8") as f:
            f.write(f"AI_API_KEY={clean_key}\n")
    except Exception as e:
        print(f"Warning: Could not write .env file: {e}")

    return get_ai_config()
