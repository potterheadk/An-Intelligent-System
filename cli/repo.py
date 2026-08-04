from __future__ import annotations

import re
import shutil
import subprocess
from pathlib import Path
from typing import Optional

from core.config import settings


def _repo_name_from_url(repository: str) -> str:
    repository = repository.rstrip("/")
    repo_name = repository.split("/")[-1]
    if repo_name.endswith(".git"):
        repo_name = repo_name[: -len(".git")]
    if not repo_name:
        raise ValueError("Could not determine repository name from URL")
    repo_name = re.sub(r"[^\w\-\.]+", "-", repo_name)
    return repo_name


def _main_project_root() -> Path:
    return Path(__file__).resolve().parents[2]


def clone_repository(repository: str, branch: Optional[str] = None, target: Optional[str] = None) -> Path:
    if target:
        destination = Path(target).expanduser().resolve()
    else:
        destination = settings.EXTERNAL_REPOS_DIR.expanduser().resolve() / _repo_name_from_url(repository)

    project_root = _main_project_root().resolve()
    if project_root in destination.parents or destination == project_root:
        raise ValueError(
            "The clone destination must be outside the main project scope for isolated repository storage."
        )

    if destination.exists() and any(destination.iterdir()):
        raise FileExistsError(f"Destination already exists and is not empty: {destination}")

    destination.parent.mkdir(parents=True, exist_ok=True)

    git_path = shutil.which("git")
    if git_path is None:
        raise RuntimeError("Git is not available on this system. Install git to use clone.")

    command = [git_path, "clone"]
    if branch:
        command.extend(["--branch", branch, "--single-branch"])
    command.extend([repository, str(destination)])

    result = subprocess.run(command, capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(
            f"Git clone command failed with code {result.returncode}: {result.stderr.strip()}"
        )

    return destination
