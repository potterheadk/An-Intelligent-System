from __future__ import annotations

import os
import readline
import sys
import termios
import tty
from pathlib import Path
from typing import Optional

from rich.console import Console
from rich.panel import Panel
from rich.prompt import Prompt
from rich.table import Table

from indexing.file_filter import (
    DEFAULT_ALLOWED_EXTENSIONS,
    DEFAULT_BLOCKED_NAMES,
    FileFilter,
)

console = Console()


def _format_directory_listing(path: Path, directories: list[Path], files: list[Path], selected_index: int = 0) -> None:
    table = Table(show_header=True, header_style="bold cyan")
    table.add_column("Type", width=10)
    table.add_column("Name")
    table.add_column("Path", overflow="fold")

    entries: list[tuple[str, str, str]] = []
    if path.parent != path:
        entries.append(("dir", "..", str(path.parent)))

    for directory in directories:
        entries.append(("dir", directory.name, str(directory)))

    for file in files:
        entries.append(("file", file.name, str(file)))

    for index, (entry_type, name, entry_path) in enumerate(entries):
        marker = ">" if index == selected_index else " "
        table.add_row(entry_type, f"{marker} {name}", entry_path)

    console.print(Panel(table, title=f"Browsing: {path}"))
    console.print("[dim]Keys: ↑/↓ select, Enter open, p path, u up, r refresh, i ignore, a allow, l rules, q quit[/dim]")


def _read_key() -> str:
    if not sys.stdin.isatty() or not sys.stdout.isatty():
        return ""

    fd = sys.stdin.fileno()
    old_settings = termios.tcgetattr(fd)
    try:
        tty.setraw(fd)
        char = sys.stdin.read(1)
        if char == "\x1b":
            seq = sys.stdin.read(2)
            if seq == "[A":
                return "up"
            if seq == "[B":
                return "down"
            return "esc"
        if char in {"\r", "\n"}:
            return "enter"
        return char
    finally:
        termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)


def _build_browser_entries(path: Path, directories: list[Path], files: list[Path]) -> list[tuple[str, Path | None]]:
    entries: list[tuple[str, Path | None]] = []
    if path.parent != path:
        entries.append(("dir", None))

    for directory in directories:
        entries.append(("dir", directory))

    for file in files:
        entries.append(("file", file))

    return entries


def _ask_path_with_completion(current_path: Path) -> Path | None:
    def completer(text: str, state: int) -> str | None:
        prefix = text or ""
        if not prefix:
            candidates = [".", ".."]
        else:
            candidates = [".", ".."]

        base_dir = current_path
        if prefix.startswith("~"):
            expanded = os.path.expanduser(prefix)
            if os.path.isdir(expanded):
                base_dir = Path(expanded)
                prefix = ""
            else:
                prefix = prefix[1:]

        if prefix.startswith("/"):
            base_dir = Path(prefix).parent if Path(prefix).parent.exists() else Path(prefix)
            prefix = Path(prefix).name
        elif os.path.sep in prefix:
            parts = prefix.split(os.path.sep)
            base_dir = current_path
            for part in parts[:-1]:
                if part in {"", "."}:
                    continue
                base_dir = base_dir / part
            prefix = parts[-1]

        try:
            entries = list(base_dir.iterdir()) if base_dir.exists() and base_dir.is_dir() else []
        except OSError:
            entries = []

        matches = []
        for entry in entries:
            name = entry.name
            if entry.is_dir():
                name = f"{name}/"
            if name.startswith(prefix):
                matches.append(name)

        if state < len(matches):
            return matches[state]
        return None

    previous_completer = readline.get_completer()
    readline.set_completer(completer)
    readline.parse_and_bind("tab: complete")
    readline.set_completer_delims("/\\")

    try:
        raw_value = input(f"Path [{current_path}] > ").strip()
    finally:
        readline.set_completer(previous_completer)

    if not raw_value:
        return None

    candidate = Path(raw_value).expanduser()
    if not candidate.is_absolute():
        candidate = (current_path / candidate).resolve()
    else:
        candidate = candidate.resolve()

    return candidate if candidate.exists() and candidate.is_dir() else None


def _ask_manual_ignore(default_ignore: str) -> str:
    return Prompt.ask(
        "Enter ignored names/folders/extensions (comma-separated)",
        default=default_ignore,
    )


def _ask_manual_allow(default_allow: str) -> str:
    return Prompt.ask(
        "Enter allowed extensions (comma-separated)",
        default=default_allow,
    )


def browse_repository(root: Path, manual_ignore: str = "", manual_allow: str = "") -> None:
    current_path = root.expanduser().resolve()
    if not current_path.exists() or not current_path.is_dir():
        raise ValueError(f"Repository root does not exist: {current_path}")

    default_ignore = ",".join(sorted(DEFAULT_BLOCKED_NAMES)) if not manual_ignore else manual_ignore
    default_allow = ",".join(sorted(DEFAULT_ALLOWED_EXTENSIONS)) if not manual_allow else manual_allow
    file_filter = FileFilter(manual_ignore=manual_ignore or default_ignore, manual_allow=manual_allow or default_allow)

    selected_index = 0

    while True:
        directories, files = file_filter.list_directory(current_path)
        entries = _build_browser_entries(current_path, directories, files)

        if selected_index >= len(entries):
            selected_index = max(0, len(entries) - 1)

        if not entries:
            console.clear()
            console.print("[yellow]No entries to browse.[/yellow]")
        else:
            console.clear()
            _format_directory_listing(current_path, directories, files, selected_index)

        if not sys.stdin.isatty() or not sys.stdout.isatty():
            choice = Prompt.ask(
                "Action",
                choices=[
                    "cd",
                    "up",
                    "refresh",
                    "ignore",
                    "allow",
                    "rules",
                    "quit",
                ],
                default="refresh",
                show_choices=True,
            )
            if choice == "cd":
                if not directories:
                    console.print("[yellow]No directories available to change into.[/yellow]")
                    continue
                target = Prompt.ask(
                    "Directory name to enter (use exact name)",
                    choices=[d.name for d in directories],
                    show_choices=True,
                )
                current_path = current_path / target
                selected_index = 0
                continue
        else:
            key = _read_key()
            if key == "up":
                selected_index = max(0, selected_index - 1)
                continue
            if key == "down":
                selected_index = min(max(0, len(entries) - 1), selected_index + 1)
                continue
            if key in {"enter", "\r", "\n"}:
                if not entries:
                    continue
                selected_entry = entries[selected_index]
                if selected_entry[0] == "dir" and selected_entry[1] is None:
                    if current_path.parent == current_path:
                        console.print("[yellow]Already at root directory.[/yellow]")
                        continue
                    current_path = current_path.parent
                    selected_index = 0
                    continue
                if selected_entry[0] == "dir" and selected_entry[1] is not None:
                    current_path = selected_entry[1]
                    selected_index = 0
                    continue
                console.print("[yellow]Select a directory to enter.[/yellow]")
                continue
            if key in {"p", "P"}:
                target_path = _ask_path_with_completion(current_path)
                if target_path is None:
                    console.print("[yellow]No valid directory path entered.[/yellow]")
                elif target_path.exists() and target_path.is_dir():
                    current_path = target_path.resolve()
                    selected_index = 0
                else:
                    console.print("[yellow]Path does not exist or is not a directory.[/yellow]")
                continue
            if key in {"u", "U"}:
                if current_path.parent == current_path:
                    console.print("[yellow]Already at root directory.[/yellow]")
                    continue
                current_path = current_path.parent
                selected_index = 0
                continue
            if key in {"r", "R"}:
                continue
            if key in {"i", "I"}:
                manual_ignore = _ask_manual_ignore(default_ignore)
                file_filter = FileFilter(manual_ignore=manual_ignore, manual_allow=manual_allow or default_allow)
                console.print(f"[green]Updated ignore rules:[/green] {manual_ignore}")
                continue
            if key in {"a", "A"}:
                manual_allow = _ask_manual_allow(default_allow)
                file_filter = FileFilter(manual_ignore=manual_ignore or default_ignore, manual_allow=manual_allow)
                console.print(f"[green]Updated allow rules:[/green] {manual_allow}")
                continue
            if key in {"l", "L"}:
                console.print(Panel.fit(
                    f"Blocked names: {sorted(file_filter.blocked_names)}\n"
                    f"Allowed extensions: {sorted(file_filter.allowed_extensions)}",
                    title="Active filters",
                ))
                continue
            if key in {"q", "Q", "\x03"}:
                console.print("[bold]Exiting repository browser.[/bold]")
                break

            choice = key.lower()
            if choice in {"", "refresh", "r"}:
                choice = "refresh"
            elif choice in {"up", "u"}:
                choice = "up"
            elif choice in {"down", "d"}:
                choice = "down"
            elif choice in {"ignore", "i"}:
                choice = "ignore"
            elif choice in {"allow", "a"}:
                choice = "allow"
            elif choice in {"rules", "l"}:
                choice = "rules"
            elif choice in {"quit", "q"}:
                choice = "quit"
            else:
                choice = "refresh"
        if not sys.stdin.isatty() or not sys.stdout.isatty():
            choice = "refresh"
        else:
            choice = "refresh"

        if choice == "cd":
            if not directories:
                console.print("[yellow]No directories available to change into.[/yellow]")
                continue
            target = Prompt.ask(
                "Directory name to enter (use exact name)",
                choices=[d.name for d in directories],
                show_choices=True,
            )
            current_path = current_path / target
            selected_index = 0
        elif choice == "up":
            if current_path.parent == current_path:
                console.print("[yellow]Already at root directory.[/yellow]")
                continue
            current_path = current_path.parent
            selected_index = 0
        elif choice == "refresh":
            continue
        elif choice == "ignore":
            manual_ignore = _ask_manual_ignore(default_ignore)
            file_filter = FileFilter(manual_ignore=manual_ignore, manual_allow=manual_allow or default_allow)
            console.print(f"[green]Updated ignore rules:[/green] {manual_ignore}")
        elif choice == "allow":
            manual_allow = _ask_manual_allow(default_allow)
            file_filter = FileFilter(manual_ignore=manual_ignore or default_ignore, manual_allow=manual_allow)
            console.print(f"[green]Updated allow rules:[/green] {manual_allow}")
        elif choice == "rules":
            console.print(Panel.fit(
                f"Blocked names: {sorted(file_filter.blocked_names)}\n"
                f"Allowed extensions: {sorted(file_filter.allowed_extensions)}",
                title="Active filters",
            ))
        elif choice == "quit":
            console.print("[bold]Exiting repository browser.[/bold]")
            break


def browse_repository_cli(root: Optional[str] = None, manual_ignore: str = "", manual_allow: str = "") -> None:
    repo_root = Path(root or Path.cwd())
    browse_repository(repo_root, manual_ignore=manual_ignore, manual_allow=manual_allow)
