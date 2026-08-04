from __future__ import annotations

import re
from pathlib import Path
from typing import Iterable

DEFAULT_BLOCKED_NAMES = {".git", "node_modules", "venv.png", "__pycache__"}
DEFAULT_ALLOWED_EXTENSIONS = {".py", ".js", ".md"}


def _normalize_name_entries(value: str) -> set[str]:
    return {
        token.strip().lower()
        for token in re.split(r"[,;\s]+", value or "")
        if token.strip()
    }


def _normalize_extensions(value: str) -> set[str]:
    normalized: set[str] = set()
    for token in re.split(r"[,;\s]+", value or ""):
        token = token.strip().lower()
        if not token:
            continue
        if not token.startswith("."):
            token = f".{token}"
        normalized.add(token)
    return normalized


class FileFilter:
    def __init__(self, manual_ignore: str = "", manual_allow: str = ""):
        self.blocked_names = DEFAULT_BLOCKED_NAMES | _normalize_name_entries(manual_ignore)
        self.allowed_names: set[str] = set()
        self.allowed_extensions = DEFAULT_ALLOWED_EXTENSIONS

        for token in _normalize_name_entries(manual_allow):
            if token.startswith("."):
                self.allowed_extensions.add(token)
            else:
                self.allowed_names.add(token)

    def is_directory_allowed(self, path: Path) -> bool:
        for part in path.parts:
            normalized = part.lower()
            if normalized in self.allowed_names:
                return True
            if normalized in self.blocked_names:
                return False
        return True

    def is_file_allowed(self, path: Path) -> bool:
        if not self.is_directory_allowed(path.parent):
            return False

        normalized_name = path.name.lower()
        if normalized_name in self.allowed_names:
            return True
        if normalized_name in self.blocked_names:
            return False

        return path.suffix.lower() in self.allowed_extensions

    def list_directory(self, directory: Path) -> tuple[list[Path], list[Path]]:
        if not directory.exists() or not directory.is_dir():
            raise ValueError(f"Directory does not exist: {directory}")

        directories: list[Path] = []
        files: list[Path] = []

        for entry in sorted(directory.iterdir(), key=lambda item: (not item.is_dir(), item.name.lower())):
            if entry.is_dir():
                if self.is_directory_allowed(entry):
                    directories.append(entry)
                continue

            if self.is_file_allowed(entry):
                files.append(entry)

        return directories, files

    def list_repository(self, root: Path) -> list[Path]:
        if not root.exists() or not root.is_dir():
            raise ValueError(f"Repository root does not exist: {root}")

        allowed_files: list[Path] = []
        for path in sorted(root.rglob("*")):
            if path.is_file() and self.is_file_allowed(path):
                allowed_files.append(path)
        return allowed_files
