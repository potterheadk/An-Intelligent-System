"""
===============================================================================
MODULE: Context Packer (codebase-agent/context/context_pack.py)
===============================================================================

PURPOSE:
--------
Assembles retrieved search results (code chunks) into structured, citation-enforced
prompt context packages for local SLMs or remote LLMs.

WHY CONTEXT PACKING MATTERS:
----------------------------
1. Citation Grounding: Explicitly formats file paths and line bounds so the model 
   can cite exact code snippets in its answers.
2. Context Window Budgeting: Truncates or caps context size to prevent exceeding
   local model context limits (e.g., 4k-8k tokens for 7B models).
3. Prompt Structure: Separates retrieved codebase evidence from user instructions
   to reduce hallucinations.

HOW IT WORKS:
-------------
1. Accepts search results from `CodeRetriever` and the user's natural language query.
2. Formats chunks with standardized markdown code blocks and citation headers.
3. Enforces a maximum character/token context budget.
4. Returns a structured `ContextPack` ready to be passed to `OllamaModel` or `GeminiModel`.

STANDALONE TESTING:
-------------------
You can test prompt context assembly in your terminal:

    python codebase-agent/context/context_pack.py "How does authentication work?"
===============================================================================
"""

import sys
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional

# Ensure package imports work when executed as a standalone script
ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

try:
    from context.retriever import SearchResult
except ImportError:
    @dataclass
    class SearchResult:
        score: float
        chunk_id: str
        relative_path: str
        start_line: int
        end_line: int
        content: str
        language: str


@dataclass
class ContextPack:
    """Assembled prompt context ready for model execution."""
    system_prompt: str
    user_prompt: str
    full_prompt: str
    total_chars: int
    chunk_count: int
    cited_files: List[str]


class ContextPacker:
    """Formats retrieved chunks into grounded model prompts."""

    DEFAULT_SYSTEM_INSTRUCTION = (
        "You are an expert codebase assistant. Answer developer questions using ONLY the provided code context.\n"
        "RULES:\n"
        "1. Every claim or code explanation MUST cite the source file and line numbers (e.g., `path/to/file.py (Lines 10-25)`).\n"
        "2. If the answer cannot be determined from the provided context, state clearly that the code context is insufficient.\n"
        "3. Do NOT invent or hallucinate file names, function signatures, or dependencies not present in the context."
    )

    def __init__(self, max_context_chars: int = 12000):
        """
        Args:
            max_context_chars: Character budget limit for context (~3,000 tokens).
        """
        self.max_context_chars = max_context_chars

    def pack(
        self,
        query: str,
        search_results: List[SearchResult],
        system_instruction: Optional[str] = None,
    ) -> ContextPack:
        """Pack retrieved chunks into a structured prompt context."""
        system_prompt = system_instruction or self.DEFAULT_SYSTEM_INSTRUCTION
        
        context_blocks: List[str] = []
        cited_files: List[str] = []
        current_chars = 0

        for idx, result in enumerate(search_results, 1):
            block_header = f"--- CONTEXT BLOCK {idx} | File: {result.relative_path} (Lines {result.start_line}-{result.end_line}) ---"
            code_block = f"```{result.language}\n{result.content}\n```"
            formatted_block = f"{block_header}\n{code_block}\n"

            # Check character budget limit
            if current_chars + len(formatted_block) > self.max_context_chars:
                break

            context_blocks.append(formatted_block)
            current_chars += len(formatted_block)
            
            file_citation = f"{result.relative_path}:{result.start_line}-{result.end_line}"
            if file_citation not in cited_files:
                cited_files.append(file_citation)

        joined_context = "\n".join(context_blocks)
        
        user_prompt = (
            f"### RELEVANT CODE CONTEXT\n"
            f"{joined_context if joined_context else 'No code context found.'}\n\n"
            f"### QUESTION\n"
            f"{query}\n\n"
            f"### ANSWER (with file & line citations):"
        )

        full_prompt = f"{system_prompt}\n\n{user_prompt}"

        return ContextPack(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            full_prompt=full_prompt,
            total_chars=len(full_prompt),
            chunk_count=len(context_blocks),
            cited_files=cited_files,
        )


# ===============================================================================
# STANDALONE MODULE TEST DRIVER
# ===============================================================================
if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Test Context Packer standalone.")
    parser.add_argument("query", type=str, nargs="?", default="How is environment configuration loaded?", help="User query.")
    args = parser.parse_args()

    print(f"\n[Context Packer Test] Assembling prompt for query: '{args.query}'\n")

    # Create dummy search results for testing
    dummy_results = [
        SearchResult(
            score=0.88,
            chunk_id="chk_001",
            relative_path="codebase-agent/core/config.py",
            start_line=1,
            end_line=20,
            content="class Settings:\n    OLLAMA_MODEL = 'qwen2.5-coder:7b'\n    OLLAMA_BASE_URL = 'http://localhost:11434'",
            language="python",
        ),
        SearchResult(
            score=0.79,
            chunk_id="chk_002",
            relative_path="codebase-agent/models/ollama.py",
            start_line=15,
            end_line=30,
            content="def __init__(self):\n    self.model_name = settings.OLLAMA_MODEL\n    self.base_url = settings.OLLAMA_BASE_URL",
            language="python",
        ),
    ]

    packer = ContextPacker(max_context_chars=8000)
    packed = packer.pack(query=args.query, search_results=dummy_results)

    print("=" * 80)
    print("ASSEMBLED FULL PROMPT:")
    print("=" * 80)
    print(packed.full_prompt)
    print("=" * 80)
    print(f"\nMetadata:")
    print(f"  Chunks Packed: {packed.chunk_count}")
    print(f"  Total Characters: {packed.total_chars} (~{packed.total_chars // 4} tokens)")
    print(f"  Cited Files: {packed.cited_files}")