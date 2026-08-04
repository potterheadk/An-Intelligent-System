"""Command line interface entry point.

This module defines the CLI for the codebase intelligence agent,
including the doctor command to validate local model connectivity.
"""

import argparse
import time
from rich.console import Console
from rich.panel import Panel

from cli.config_ui import run_config_ui
from cli.file_browser import browse_repository_cli
from cli.repo import clone_repository
from models.gemini import GeminiModel
from models.ollama import OllamaModel
from core.config import settings


console = Console()

RETRY_ATTEMPTS = 4
RETRY_WAIT_SECONDS = 10


def _create_model() -> object:
    if settings.MODEL_PROVIDER == "gemini":
        return GeminiModel()
    return OllamaModel()


def _retry(callable_obj, name: str) -> bool:
    for attempt in range(1, RETRY_ATTEMPTS + 1):
        console.print(f"[blue]Checking {name} (attempt {attempt}/{RETRY_ATTEMPTS})...[/blue]")
        if callable_obj():
            return True
        if attempt < RETRY_ATTEMPTS:
            console.print(
                f"[yellow]{name} not ready yet. Waiting {RETRY_WAIT_SECONDS}s before retrying...[/yellow]"
            )
            time.sleep(RETRY_WAIT_SECONDS)
    return False


def doctor() -> None:
    console.print(Panel.fit("Codebase Intelligence Agent — Phase 0 Doctor"))

    console.print(f"[bold]Selected provider:[/bold] {settings.MODEL_PROVIDER}")
    console.print(f"[bold]Ollama URL:[/bold] {settings.OLLAMA_BASE_URL}")
    console.print(f"[bold]Ollama Model:[/bold] {settings.OLLAMA_MODEL}")
    console.print(f"[bold]Gemini URL:[/bold] {settings.GEMINI_BASE_URL}")
    console.print(f"[bold]Gemini Model:[/bold] {settings.GEMINI_MODEL}")
    console.print(f"[bold]Data Dir:[/bold] {settings.DATA_DIR}")
    console.print(f"[bold]Repos Dir:[/bold] {settings.REPOS_DIR}")
    console.print(f"[bold]External repos dir:[/bold] {settings.EXTERNAL_REPOS_DIR}")
    console.print(f"[bold]Internal repos path:[/bold] {settings.INTERNAL_REPOS_PATH}")
    console.print(f"[bold]SQLite DB Path:[/bold] {settings.SQLITE_DB_PATH}")

    ollama_model = OllamaModel()
    gemini_model = GeminiModel()

    console.print(Panel.fit("Model provider health checks"))

    ollama_ready = _retry(ollama_model.healthcheck, "Ollama")
    gemini_ready = _retry(gemini_model.healthcheck, "Gemini")

    if not ollama_ready:
        console.print("[red]Ollama healthcheck failed after retries.[/red]")
        console.print("Make sure the Ollama endpoint is reachable and the model has finished loading.")
    else:
        console.print("[green]Ollama healthcheck passed.[/green]")

    if not gemini_ready:
        console.print("[red]Gemini healthcheck failed after retries.[/red]")
        console.print("Make sure GEMINI_API_KEY is set and the Gemini endpoint is reachable.")
    else:
        console.print("[green]Gemini healthcheck passed.[/green]")

    console.print(Panel.fit("Model generation test"))

    prompt = """
You are helping test a local codebase intelligence CLI.
Reply with one short sentence only:
"Local model connection is working."
"""

    if ollama_ready:
        try:
            console.print("[bold]Ollama generation response:[/bold]")
            response = ollama_model.generate(prompt)
            console.print(Panel(response))
        except Exception as exc:
            console.print("[red]Ollama generation failed.[/red]")
            console.print(str(exc))

    if gemini_ready:
        try:
            console.print("[bold]Gemini generation response:[/bold]")
            response = gemini_model.generate(prompt)
            console.print(Panel(response))
        except Exception as exc:
            console.print("[red]Gemini generation failed.[/red]")
            console.print(str(exc))


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="codebase-agent",
        description="Local Codebase Intelligence Agent",
    )

    subparsers = parser.add_subparsers(dest="command")

    subparsers.add_parser(
        "doctor",
        help="Check local environment and Ollama connection",
    )
    subparsers.add_parser(
        "config",
        help="Open the interactive configuration editor",
    )

    clone_parser = subparsers.add_parser(
        "clone",
        help="Clone a repository into the isolated external repos directory",
    )
    clone_parser.add_argument("repository", help="Repository URL to clone")
    clone_parser.add_argument(
        "--branch",
        help="Git branch to clone",
        default=None,
    )
    clone_parser.add_argument(
        "--target",
        help="Optional target directory outside the main project scope",
        default=None,
    )

    browse_parser = subparsers.add_parser(
        "browse",
        help="Browse a repository tree using file filters",
    )
    browse_parser.add_argument(
        "--root",
        help="Root path to browse",
        default=None,
    )
    browse_parser.add_argument(
        "--ignore",
        help="Comma-separated manual ignore names/extensions",
        default="",
    )
    browse_parser.add_argument(
        "--allow",
        help="Comma-separated manual allowed extensions",
        default="",
    )

    args = parser.parse_args()

    if args.command == "doctor":
        doctor()
    elif args.command == "config":
        run_config_ui()
    elif args.command == "clone":
        try:
            destination = clone_repository(args.repository, branch=args.branch, target=args.target)
            console.print(f"[green]Repository cloned to:[/green] {destination}")
        except Exception as exc:
            console.print(f"[red]Clone failed:[/red] {exc}")
    elif args.command == "browse":
        browse_repository_cli(root=args.root, manual_ignore=args.ignore, manual_allow=args.allow)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()