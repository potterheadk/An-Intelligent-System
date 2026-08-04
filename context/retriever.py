"""
===============================================================================
MODULE: Code Retriever (codebase-agent/context/retriever.py)
===============================================================================

PURPOSE:
--------
Performs similarity-based vector retrieval over indexed code chunks to identify the
most relevant code snippets for a user query.

HOW IT WORKS:
-------------
1. Query Embedding: Converts the user's natural language question into an embedding vector.
2. Cosine Similarity: Calculates the dot product between the query vector and all chunk vectors:
   
       Similarity(q, c) = (q · c) / (||q|| * ||c||)

3. Ranking: Sorts chunks by similarity score (1.0 = identical, 0.0 = orthogonal).
4. Top-K Selection: Returns the top K highest-scoring chunks with full citation details.

STANDALONE TESTING:
-------------------
You can test the full pipeline (Scanning -> Chunking -> Embedding -> Retrieval) standalone:

    python codebase-agent/context/retriever.py codebase-agent "Where is model generation handled?"
===============================================================================
"""

import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional, Tuple

# Ensure package imports work when executed as a standalone script
ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

try:
    import numpy as np
    from indexing.embedder import CodeEmbedder, VectorizedChunk
    from indexing.scanner import RepositoryScanner
    from indexing.chunker import CodeChunker, CodeChunk
    HAS_DEPENDENCIES = True
except ImportError:
    HAS_DEPENDENCIES = False


@dataclass
class SearchResult:
    """SearchResult containing similarity score and code chunk metadata."""
    score: float
    chunk_id: str
    relative_path: str
    start_line: int
    end_line: int
    content: str
    language: str


class CodeRetriever:
    """In-memory vector similarity retriever for Phase 1 RAG experiments."""

    def __init__(self, embedder: Optional[CodeEmbedder] = None):
        if not HAS_DEPENDENCIES:
            raise RuntimeError("Missing required dependencies for retrieval. Run: pip install numpy sentence-transformers")
        
        self.embedder = embedder or CodeEmbedder()
        self.indexed_chunks: List[CodeChunk] = []
        self.embeddings_matrix: Optional[np.ndarray] = None

    def index_chunks(self, chunks: List[CodeChunk]) -> int:
        """Embed and index a list of code chunks."""
        if not chunks:
            self.indexed_chunks = []
            self.embeddings_matrix = None
            return 0

        self.indexed_chunks = chunks
        texts = [chunk.content for chunk in chunks]
        
        raw_vectors = self.embedder.embed_batch(texts)
        self.embeddings_matrix = np.array(raw_vectors, dtype=np.float32)
        return len(chunks)

    def retrieve(self, query: str, top_k: int = 5) -> List[SearchResult]:
        """Retrieve top_k code chunks most relevant to the natural language query."""
        if self.embeddings_matrix is None or len(self.indexed_chunks) == 0:
            return []

        # Generate query vector
        query_vector = np.array(self.embedder.embed_text(query), dtype=np.float32)

        # Compute cosine similarity via matrix dot product (vectors are already L2 normalized)
        scores = np.dot(self.embeddings_matrix, query_vector)

        # Get indices of top_k highest scores
        top_indices = np.argsort(scores)[::-1][:top_k]

        results: List[SearchResult] = []
        for idx in top_indices:
            score = float(scores[idx])
            chunk = self.indexed_chunks[idx]
            results.append(
                SearchResult(
                    score=round(score, 4),
                    chunk_id=chunk.chunk_id,
                    relative_path=chunk.relative_path,
                    start_line=chunk.start_line,
                    end_line=chunk.end_line,
                    content=chunk.content,
                    language=chunk.language,
                )
            )

        return results


# ===============================================================================
# STANDALONE MODULE TEST DRIVER
# ===============================================================================
if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Test Code Retriever pipeline standalone.")
    parser.add_argument("repo_path", type=str, help="Directory/Repo to scan, index, and query.")
    parser.add_argument("query", type=str, help="Search query (e.g., 'How is configuration loaded?')")
    parser.add_argument("--top-k", type=int, default=3, help="Number of results to return.")
    args = parser.parse_args()

    print(f"\n[Retriever Test] Scanning target directory: {args.repo_path}")
    scanner = RepositoryScanner()
    files = scanner.scan(args.repo_path)
    
    print(f"[Retriever Test] Found {len(files)} files. Chunking content...")
    chunker = CodeChunker(chunk_size_lines=35, overlap_lines=5)
    all_chunks = []
    for f in files:
        all_chunks.extend(chunker.chunk_file(f))

    print(f"[Retriever Test] Total Chunks: {len(all_chunks)}. Embedding into vector index...")
    start_time = time.perf_counter()
    retriever = CodeRetriever()
    retriever.index_chunks(all_chunks)
    index_time = (time.perf_counter() - start_time) * 1000.0
    print(f"[Retriever Test] Index built in {index_time:.2f} ms")

    print(f"\n[Retriever Test] Executing query: '{args.query}' (top {args.top_k})\n")
    search_start = time.perf_counter()
    results = retriever.retrieve(args.query, top_k=args.top_k)
    search_time = (time.perf_counter() - search_start) * 1000.0

    print(f"Retrieval finished in {search_time:.2f} ms\n" + "=" * 80)
    for idx, r in enumerate(results, 1):
        print(f"RANK {idx} | SCORE: {r.score} | FILE: {r.relative_path} (Lines {r.start_line}-{r.end_line})")
        print("-" * 80)
        preview = "\n".join(r.content.splitlines()[:5])
        print(preview)
        if len(r.content.splitlines()) > 5:
            print("...")
        print("=" * 80 + "\n")