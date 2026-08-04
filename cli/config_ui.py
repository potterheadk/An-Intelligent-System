from __future__ import annotations

from typing import Any

from rich.console import Console
from rich.panel import Panel
from rich.prompt import Confirm, Prompt
from rich.table import Table

from core.config import ENV_KEYS, load_env_values, load_settings, write_env_values

console = Console()

CONFIG_KEYS = [
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

FIELD_LABELS: dict[str, str] = {
    "MODEL_PROVIDER": "Model provider",
    "OLLAMA_BASE_URL": "Ollama base URL",
    "OLLAMA_MODEL": "Ollama model",
    "GEMINI_BASE_URL": "Gemini base URL",
    "GEMINI_MODEL": "Gemini model",
    "GEMINI_API_KEY": "Gemini API key",
    "GROQ_API_KEY": "GROQ API key",
    "EXTERNAL_REPOS_DIR": "External repo clone directory",
    "INTERNAL_REPOS_PATH": "Internal repo path",
    "DATA_DIR": "Data directory",
    "REPOS_DIR": "Repositories directory",
    "VECTOR_DIR": "Vector directory",
    "CACHE_DIR": "Cache directory",
    "SQLITE_DB_PATH": "SQLite database path",
}

DEFAULT_PROVIDER_OPTIONS = ["ollama", "gemini"]


def _make_table(values: dict[str, str]) -> Table:
    table = Table(show_header=True, header_style="bold cyan")
    table.add_column("Setting")
    table.add_column("Value", overflow="fold")

    for key in CONFIG_KEYS:
        table.add_row(FIELD_LABELS.get(key, key), values.get(key, ""))

    return table


def _edit_field(values: dict[str, str], key: str, description: str) -> None:
    current = values.get(key, "")
    if key == "MODEL_PROVIDER":
        answer = Prompt.ask(
            f"{description}",
            choices=DEFAULT_PROVIDER_OPTIONS,
            default=current or "ollama",
            show_choices=True,
        )
    else:
        answer = Prompt.ask(f"{description}", default=current)

    values[key] = answer.strip()


def _edit_api_keys(values: dict[str, str]) -> None:
    console.print(Panel.fit("Edit API keys", title="API Keys"))
    for key in ["GEMINI_API_KEY", "GROQ_API_KEY"]:
        _edit_field(values, key, FIELD_LABELS[key])


def _edit_links(values: dict[str, str]) -> None:
    console.print(Panel.fit("Edit service links and URLs", title="Links"))
    for key in ["OLLAMA_BASE_URL", "GEMINI_BASE_URL"]:
        _edit_field(values, key, FIELD_LABELS[key])


def _edit_provider_settings(values: dict[str, str]) -> None:
    console.print(Panel.fit("Edit provider settings", title="Provider"))
    for key in ["MODEL_PROVIDER", "OLLAMA_MODEL", "GEMINI_MODEL"]:
        _edit_field(values, key, FIELD_LABELS[key])


def _edit_repo_paths(values: dict[str, str]) -> None:
    console.print(Panel.fit("Edit repository path settings", title="Repository paths"))
    for key in ["EXTERNAL_REPOS_DIR", "INTERNAL_REPOS_PATH"]:
        _edit_field(values, key, FIELD_LABELS[key])


def _save(values: dict[str, str]) -> None:
    write_env_values(values)
    _ = load_settings()
    console.print("[green]Configuration saved to disk successfully.[/green]")


def run_config_ui() -> None:
    values = load_env_values()
    changed = False

    console.print(Panel.fit("Configuration editor — Phase 1", title="Config UI"))

    while True:
        status = "[bold yellow]Unsaved changes[/bold yellow]" if changed else "[green]All changes saved[/green]"
        console.print(f"Current status: {status}")
        console.print(_make_table(values))

        choice = Prompt.ask(
            "Select an action",
            choices=["preview", "provider", "apikeys", "links", "paths", "save", "exit"],
            default="preview",
            show_choices=True,
        )

        if choice == "preview":
            console.print(Panel(_make_table(values), title="Current config"))
        elif choice == "provider":
            _edit_provider_settings(values)
            changed = True
        elif choice == "apikeys":
            _edit_api_keys(values)
            changed = True
        elif choice == "links":
            _edit_links(values)
            changed = True
        elif choice == "paths":
            _edit_repo_paths(values)
            changed = True
        elif choice == "save":
            _save(values)
            changed = False
        elif choice == "exit":
            if changed and Confirm.ask("You have unsaved changes. Save before exiting?", default=True):
                _save(values)
            break

    console.print("[bold]Exiting configuration editor.[/bold]")
