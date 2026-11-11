"""Configuration from environment variables."""
import os
from dataclasses import dataclass


@dataclass(frozen=True)
class Config:
    chat_model: str
    embed_model: str
    ollama_url: str
    min_score: float


def load(env=None):
    """Build the configuration from env (default: os.environ)."""
    env = os.environ if env is None else env
    return Config(
        chat_model=env.get("ASKFILES_CHAT_MODEL", "qwen2.5:7b"),
        embed_model=env.get("ASKFILES_EMBED_MODEL", "nomic-embed-text"),
        ollama_url=env.get("ASKFILES_OLLAMA_URL", "http://localhost:11434").rstrip("/"),
        min_score=float(env.get("ASKFILES_MIN_SCORE", "0.35")),
    )
