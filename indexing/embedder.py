"""
===============================================================================
MODULE: Local Code Embedder (codebase-agent/indexing/embedder.py)
===============================================================================

PURPOSE:
--------
Converts text and code chunks into dense vector embeddings using local, zero-cost
transformer models (`sentence-transformers`).

HOW IT WORKS:
-------------
1. Model Selection: Uses `all-MiniLM-L6-v2` by default (384-dimensional vectors, 
   lightweight, fast on standard CPUs).
2. Vectorization: Encodes code snippets into normalized floating-point arrays.
3. Dimensionality: Embeddings capture semantic meaning rather than exact keyword matches.
   For instance, "user login" and "authenticate_session()" will have high cosine similarity.

DESIGN PARAMETERS:
------------------
- model_name: Any huggingface sentence-transformer (e.g. `BAAI/bge-small-en-v1.5`, 
  `all-MiniLM-L6-v2`).
- normalize_embeddings: Normalizes vectors to unit length (L2 norm = 1.0) so 
  cosine similarity can be computed via dot product: `dot(u, v)`.

STANDALONE TESTING:
-------------------
You can test embedding generation and verify vector dimensions in your terminal:

    python codebase-agent/indexing/embedder.py "def authenticate(user, password):"
===============================================================================
"""

import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import List, Union, Dict, Any

# Ensure package imports work when executed as a standalone script
ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

try:
    import numpy as np
    from sentence_transformers import SentenceTransformer
    HAS_DEPENDENCIES = True
except ImportError:
    HAS_DEPENDENCIES = False


@dataclass
class VectorizedChunk:
    """Combines a code chunk with its corresponding embedding vector."""
    chunk_id: str
    relative_path: str
    start_line: int
    end_line: int
    content: str
    embedding: List[float]


class CodeEmbedder:
    """Local embedding engine powered by sentence-transformers."""

    def __init__(
        self, 
        model_name: str = "all-MiniLM-L6-v2", 
        device: str = "cpu"
    ):
        if not HAS_DEPENDENCIES:
            raise RuntimeError(
                "Missing dependencies for local embeddings.\n"
                "Please install sentence-transformers and numpy:\n"
                "  pip install sentence-transformers numpy"
            )
        
        self.model_name = model_name
        self.device = device
        self._model = None

    @property
    def model(self) -> SentenceTransformer:
        """Lazy loader for the transformer model."""
        if self._model is None:
            self._model = SentenceTransformer(self.model_name, device=self.device)
        return self._model

    def embed_text(self, text: str) -> List[float]:
        """Convert a single string/query into a normalized float embedding vector."""
        vec = self.model.encode(
            text, 
            convert_to_numpy=True, 
            normalize_embeddings=True
        )
        return vec.tolist()

    def embed_batch(self, texts: List[str]) -> List[List[float]]:
        """Convert a batch of strings into embedding vectors."""
        if not texts:
            return []
        
        vecs = self.model.encode(
            texts, 
            batch_size=32, 
            convert_to_numpy=True, 
            normalize_embeddings=True,
            show_progress_bar=False
        )
        return vecs.tolist()


# ===============================================================================
# STANDALONE MODULE TEST DRIVER
# ===============================================================================
if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Test Code Embedder standalone.")
    parser.add_argument(
        "text", 
        type=str, 
        nargs="?", 
        default="def login(username, password): return auth_service.verify(username, password)",
        help="Text or code snippet to embed."
    )
    args = parser.parse_args()

    print(f"\n[Embedder Test] Loading model and embedding input...")
    if not HAS_DEPENDENCIES:
        print("ERROR: sentence-transformers is not installed. Run: pip install sentence-transformers numpy")
        sys.exit(1)

    start = time.perf_counter()
    embedder = CodeEmbedder()
    vector = embedder.embed_text(args.text)
    elapsed_ms = (time.perf_counter() - start) * 1000.0

    print(f"[Embedder Test] Done in {elapsed_ms:.2f} ms")
    print(f"  Model: {embedder.model_name}")
    print(f"  Vector Dimensions: {len(vector)}")
    print(f"  Sample Vector Values (first 5): {vector[:5]}")