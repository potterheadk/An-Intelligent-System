"""
===============================================================================
MODULE: Repository Scanner (codebase-agent/indexing/scanner.py)
===============================================================================

PURPOSE:
--------
Discovers, filters, and inspects files within a cloned repository to prepare them
for indexing and chunking. It acts as the deterministic entry point for the 
Phase 1 Code Intelligence Core.

HOW IT WORKS:
-------------
1. Directory Walk: Recursively traverses a target repository directory.
2. Filtering: Respects file/directory ignore rules via `file_filter.py` 
   (skips `.git`, `.venv`, node_modules, binary files, lockfiles, etc.).
3. Inspection: Reads valid text files, extracts file metadata (size, line count, 
   language/stack detection, line content).
4. Data Structuring: Returns a list of structured `ScannedFile` objects.

DESIGN PARAMETERS & EXPERIMENTATION:
------------------------------------
- max_file_size_kb: Prevents token-bloat and OOM by skipping oversized files 
  (e.g., compiled JS bundles, huge JSON logs).
- language_map: Maps extensions to language identities for AST/syntax context.

STANDALONE TESTING:
-------------------
You can test this scanner individually on any directory without running the full agent:

    python codebase-agent/indexing/scanner.py /path/to/target/repo
===============================================================================
"""

import os
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional

# Ensure package imports work when executed as a standalone script
ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

try:
    from indexing.file_filter import is_ignored_file, is_ignored_dir
except ImportError:
    # Fallback placeholders if file_filter module isn't loaded
    def is_ignored_file(path: Path) -> bool:
        return path.name.startswith(".") or path.suffix in [".pyc", ".png", ".jpg", ".exe", ".bin"]

    def is_ignored_dir(path: Path) -> bool:
        return path.name in [".git", ".venv", "node_modules", "__pycache__", "dist", "build"]


@dataclass
class ScannedFile:
    """Structured representation of a scanned source code file."""
    file_path: Path
    relative_path: str
    language: str
    size_bytes: int
    line_count: int
    content: str


class RepositoryScanner:
    """Configurable repository file scanner."""

    EXTENSION_LANGUAGE_MAP = {
        ".py": "python",
        ".js": "javascript",
        ".ts": "typescript",
        ".jsx": "react",
        ".tsx": "react_ts",
        ".go": "go",
        ".rs": "rust",
        ".java": "java",
        ".c": "c",
        ".cpp": "cpp",
        ".h": "c_header",
        ".html": "html",
        ".css": "css",
        ".json": "json",
        ".yaml": "yaml",
        ".yml": "yaml",
        ".md": "markdown",
        ".sql": "sql",
        ".sh": "bash",
        ".dockerfile": "docker",
    }

    def __init__(self, max_file_size_kb: int = 500):
        self.max_file_size_bytes = max_file_size_kb * 1024

    def detect_language(self, path: Path) -> str:
        """Detect the programming language or format based on extension/filename."""
        filename = path.name.lower()
        if filename == "dockerfile":
            return "docker"
        if filename == "makefile":
            return "makefile"
        
        ext = path.suffix.lower()
        return self.EXTENSION_LANGUAGE_MAP.get(ext, "text")

    def scan(self, repo_path: Path | str) -> List[ScannedFile]:
        """Walk the target repository and collect valid, filtered source files."""
        repo_root = Path(repo_path).resolve()
        if not repo_root.exists() or not repo_root.is_dir():
            raise ValueError(f"Invalid repository path: {repo_root}")

        scanned_files: List[ScannedFile] = []

        for root, dirs, files in os.walk(repo_root):
            current_dir = Path(root)

            # Filter out ignored directories in-place to prevent traversing into them
            dirs[:] = [
                d for d in dirs 
                if not is_ignored_dir(current_dir / d)
            ]

            for file in files:
                file_path = current_dir / file

                # Skip ignored files
                if is_ignored_file(file_path):
                    continue

                # Check file size limit
                try:
                    file_size = file_path.stat().st_size
                except OSError:
                    continue

                if file_size > self.max_file_size_bytes or file_size == 0:
                    continue

                # Read content safely with UTF-8 fallback
                try:
                    content = file_path.read_text(encoding="utf-8", errors="replace")
                except Exception:
                    continue

                lines = content.splitlines()
                relative_path = str(file_path.relative_to(repo_root))
                language = self.detect_language(file_path)

                scanned_files.append(
                    ScannedFile(
                        file_path=file_path,
                        relative_path=relative_path,
                        language=language,
                        size_bytes=file_size,
                        line_count=len(lines),
                        content=content,
                    )
                )

        return scanned_files


# ===============================================================================
# STANDALONE MODULE TEST DRIVER
# ===============================================================================
if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Test Repository Scanner standalone.")
    parser.add_argument("target_path", type=str, help="Path to repository or directory to scan.")
    parser.add_argument("--max-kb", type=int, default=500, help="Max file size in KB.")
    args = parser.parse_args()

    print(f"\n[Scanner Test] Scanning: {args.target_path}")
    scanner = RepositoryScanner(max_file_size_kb=args.max_kb)
    results = scanner.scan(args.target_path)

    print(f"[Scanner Test] Total files scanned: {len(results)}\n")
    print(f"{'RELATIVE PATH':<45} | {'LANG':<12} | {'LINES':<6} | {'SIZE (KB)':<8}")
    print("-" * 80)

    for item in results[:15]:  # Print first 15 files
        size_kb = round(item.size_bytes / 1024, 2)
        print(f"{item.relative_path[:45]:<45} | {item.language:<12} | {item.line_count:<6} | {size_kb:<8}")

    if len(results) > 15:
        print(f"... and {len(results) - 15} more files.")