"""Application configuration.

This module loads environment variables and exposes application settings
for model providers, directories, and storage paths.
"""
from pathlib import Path
from dotenv import dotenv_values, load_dotenv
import os


BASE_DIR = Path(__file__).resolve().parent.parent
ENV_PATH = BASE_DIR / ".env"
load_dotenv(dotenv_path=ENV_PATH)
ENV_KEYS = [
    "MODEL_PROVIDER",
    "OLLAMA_BASE_URL",
    "OLLAMA_MODEL",
    "GEMINI_BASE_URL",
    "GEMINI_MODEL",
    "GEMINI_API_KEY",
    "GROQ_API_KEY",
    "EXTERNAL_REPOS_DIR",
    "INTERNAL_REPOS_PATH",
    "DATA_DIR",
    "REPOS_DIR",
    "VECTOR_DIR",
    "CACHE_DIR",
    "SQLITE_DB_PATH",
]


def load_settings() -> "Settings":
    load_dotenv(dotenv_path=ENV_PATH)
    return Settings()


def load_env_values() -> dict[str, str]:
    raw = dotenv_values(dotenv_path=ENV_PATH)
    values = {k: v if v is not None else "" for k, v in raw.items() if k is not None}
    for key in ENV_KEYS:
        values.setdefault(key, "")
    return values


def write_env_values(values: dict[str, str]) -> None:
    lines = [f"{key}={values.get(key, "")}" for key in ENV_KEYS]
    ENV_PATH.write_text("\n".join(lines) + "\n", encoding="utf-8")


class Settings:
    MODEL_PROVIDER: str = os.getenv("MODEL_PROVIDER", "ollama").lower()

    OLLAMA_BASE_URL: str = os.getenv("OLLAMA_BASE_URL")
    OLLAMA_MODEL: str = os.getenv("OLLAMA_MODEL")

    GEMINI_BASE_URL: str = os.getenv(
        "GEMINI_BASE_URL",
        "https://generativelanguage.googleapis.com/v1beta/openai",
    )
    GEMINI_MODEL: str = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")
    GEMINI_API_KEY: str = os.getenv("GEMINI_API_KEY", "")
    GROQ_API_KEY: str = os.getenv("GROQ_API_KEY", "")

    DATA_DIR: Path = Path(os.getenv("DATA_DIR", "data"))
    REPOS_DIR: Path = Path(os.getenv("REPOS_DIR", "data/repos"))
    EXTERNAL_REPOS_DIR: Path = Path(
        os.getenv("EXTERNAL_REPOS_DIR", str(BASE_DIR.parent / "external_repos"))
    ).expanduser()
    INTERNAL_REPOS_PATH: Path = Path(
        os.getenv("INTERNAL_REPOS_PATH", str(BASE_DIR / "data/repos/internal"))
    ).expanduser()
    VECTOR_DIR: Path = Path(os.getenv("VECTOR_DIR", "data/vector"))
    CACHE_DIR: Path = Path(os.getenv("CACHE_DIR", "data/cache"))
    SQLITE_DB_PATH: Path = Path(os.getenv("SQLITE_DB_PATH", "data/agent.db"))


settings = Settings()