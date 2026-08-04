"""
===============================================================================
MODULE: Code Chunker (codebase-agent/indexing/chunker.py)
===============================================================================

PURPOSE:
--------
Splits raw file contents into smaller, distinct code chunks suitable for 
embedding and retrieval.

WHY CHUNKING MATTERS:
--------------------
- Too large: Includes noise and irrelevant code, exceeding model context limits.
- Too small: Loses crucial context (e.g., a function split mid-logic).
- Overlap: Ensures code constructs spanning chunk boundaries aren't missed.

HOW IT WORKS:
-------------
1. Takes a `ScannedFile` or raw content string.
2. Applies a sliding window across lines (`chunk_size_lines` with `overlap_lines`).
3. Generates deterministic `chunk_id` hashes and counts estimated tokens.
4. Outputs structured `CodeChunk` objects containing file metadata and line bounds.

STANDALONE TESTING:
-------------------
You can test chunking strategies standalone on any file:

    python codebase-agent/indexing/chunker.py /path/to/some/file.py --lines 40 --overlap 10
===============================================================================
"""

import hashlib
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional

# Ensure package imports work when executed as a standalone script
ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

try:
    from indexing.scanner import ScannedFile
except ImportError:
    @dataclass
    class ScannedFile:
        file_path: Path
        relative_path: str
        language: str
        size_bytes: int
        line_count: int
        content: str


@dataclass
class CodeChunk:
    """Structured code chunk ready for embedding and indexing."""
    chunk_id: str
    relative_path: str
    language: str
    start_line: int
    end_line: int
    content: str
    token_estimate: int


class CodeChunker:
    """Configurable sliding-window code chunker."""

    def __init__(
        self,
        chunk_size_lines: int = 50,
        overlap_lines: int = 10,
    ):
        if overlap_lines >= chunk_size_lines:
            raise ValueError("overlap_lines must be smaller than chunk_size_lines")
        
        self.chunk_size_lines = chunk_size_lines
        self.overlap_lines = overlap_lines

    def _estimate_tokens(self, text: str) -> int:
        """Rough token estimation (approx 4 chars per token for code)."""
        return max(1, len(text) // 4)

    def _generate_chunk_id(self, relative_path: str, start_line: int, end_line: int, content: str) -> str:
        """Generate a deterministic hash ID for a chunk."""
        raw = f"{relative_path}:{start_line}-{end_line}:{content}"
        return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:16]

    def chunk_file(self, scanned_file: ScannedFile) -> List[CodeChunk]:
        """Split a scanned file into code chunks using line-window strategy."""
        lines = scanned_file.content.splitlines()
        total_lines = len(lines)
        chunks: List[CodeChunk] = []

        if total_lines == 0:
            return chunks

        # If file is smaller than chunk size, return it as a single chunk
        if total_lines <= self.chunk_size_lines:
            chunk_content = "\n".join(lines)
            chunk_id = self._generate_chunk_id(scanned_file.relative_path, 1, total_lines, chunk_content)
            chunks.append(
                CodeChunk(
                    chunk_id=chunk_id,
                    relative_path=scanned_file.relative_path,
                    language=scanned_file.language,
                    start_line=1,
                    end_line=total_lines,
                    content=chunk_content,
                    token_estimate=self._estimate_tokens(chunk_content),
                )
            )
            return chunks

        # Sliding window chunking
        step = self.chunk_size_lines - self.overlap_lines
        for start_idx in range(0, total_lines, step):
            end_idx = min(start_idx + self.chunk_size_lines, total_lines)
            chunk_lines = lines[start_idx:end_idx]
            
            if not chunk_lines:
                break

            chunk_content = "\n".join(chunk_lines)
            start_line = start_idx + 1
            end_line = end_idx

            chunk_id = self._generate_chunk_id(scanned_file.relative_path, start_line, end_line, chunk_content)

            chunks.append(
                CodeChunk(
                    chunk_id=chunk_id,
                    relative_path=scanned_file.relative_path,
                    language=scanned_file.language,
                    start_line=start_line,
                    end_line=end_line,
                    content=chunk_content,
                    token_estimate=self._estimate_tokens(chunk_content),
                )
            )

            if end_idx >= total_lines:
                break

        return chunks


# ===============================================================================
# STANDALONE MODULE TEST DRIVER
# ===============================================================================
if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Test Code Chunker standalone.")
    parser.add_argument("file_path", type=str, help="Path to a single file to chunk and test.")
    parser.add_argument("--lines", type=int, default=30, help="Chunk window size in lines.")
    parser.add_argument("--overlap", type=int, default=5, help="Line overlap between chunks.")
    args = parser.parse_args()

    target_path = Path(args.file_path).resolve()
    if not target_path.exists() or not target_path.is_file():
        print(f"Error: File not found: {target_path}")
        sys.exit(1)

    print(f"\n[Chunker Test] Target File: {target_path.name}")
    content = target_path.read_text(encoding="utf-8", errors="replace")
    dummy_scanned = ScannedFile(
        file_path=target_path,
        relative_path=target_path.name,
        language="python",
        size_bytes=len(content.encode("utf-8")),
        line_count=len(content.splitlines()),
        content=content,
    )

    chunker = CodeChunker(chunk_size_lines=args.lines, overlap_lines=args.overlap)
    chunks = chunker.chunk_file(dummy_scanned)

    print(f"[Chunker Test] Total Lines: {dummy_scanned.line_count} | Total Chunks Created: {len(chunks)}\n")

    for idx, c in enumerate(chunks, 1):
        print(f"--- CHUNK {idx}/{len(chunks)} | ID: {c.chunk_id} | Lines: {c.start_line}-{c.end_line} | Tokens: ~{c.token_estimate} ---")
        preview = "\n".join(c.content.splitlines()[:4])  # Print first 4 lines of chunk
        print(preview)
        if len(c.content.splitlines()) > 4:
            print("...")
        print("-" * 70)