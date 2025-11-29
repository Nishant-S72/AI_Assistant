"""JSON-based vector store adapter (fallback when Chroma unavailable)."""
import json
import os
from pathlib import Path
from typing import List, Dict, Any
from app.clients.vectorstore import VectorQueryResult
from app.services.embeddings import get_embedding


class JSONVectorStore:
    """Simple JSON-based vector store for RAG."""
    
    def __init__(self):
        # Try multiple paths for storage
        possible_paths = [
            Path(__file__).parent.parent.parent.parent / "backend" / "storage" / "vectors.json",
            Path(__file__).parent.parent.parent.parent / "storage" / "vectors.json",
            Path.cwd() / "backend" / "storage" / "vectors.json",
            Path.cwd() / "storage" / "vectors.json",
        ]
        
        self.file_path = None
        for path in possible_paths:
            if path.parent.exists():
                self.file_path = path
                break
        
        if not self.file_path:
            # Create default path
            default_path = Path.cwd() / "backend_python" / "storage" / "vectors.json"
            default_path.parent.mkdir(parents=True, exist_ok=True)
            self.file_path = default_path
        
        self.vectors: Dict[str, Dict[str, Any]] = {}
        self.load()
    
    def load(self):
        """Load vectors from JSON file."""
        try:
            if self.file_path.exists():
                with open(self.file_path, "r", encoding="utf-8") as f:
                    stored = json.load(f)
                    if isinstance(stored, list):
                        self.vectors = {v["id"]: v for v in stored}
                    else:
                        self.vectors = stored
                print(f"[VectorStore] Loaded {len(self.vectors)} vectors from JSON")
        except Exception as e:
            print(f"[VectorStore] Could not load JSON store: {e}")
            self.vectors = {}
    
    def save(self):
        """Save vectors to JSON file."""
        try:
            with open(self.file_path, "w", encoding="utf-8") as f:
                json.dump(list(self.vectors.values()), f, indent=2)
        except Exception as e:
            print(f"[VectorStore] Error saving JSON store: {e}")
    
    def cosine_similarity(self, a: List[float], b: List[float]) -> float:
        """Calculate cosine similarity between two vectors."""
        if len(a) != len(b):
            return 0.0
        
        dot_product = sum(x * y for x, y in zip(a, b))
        norm_a = sum(x * x for x in a) ** 0.5
        norm_b = sum(x * x for x in b) ** 0.5
        
        if norm_a == 0 or norm_b == 0:
            return 0.0
        
        return dot_product / (norm_a * norm_b)


_json_store = JSONVectorStore()


async def query_json_store(query_text: str, k: int = 3) -> List[VectorQueryResult]:
    """Query JSON vector store."""
    # Get embedding for query
    query_embedding = await get_embedding(query_text)
    
    # Calculate similarities
    results = []
    for vec_id, vec_data in _json_store.vectors.items():
        if "embedding" not in vec_data:
            continue
        
        score = _json_store.cosine_similarity(query_embedding, vec_data["embedding"])
        results.append(VectorQueryResult(
            id=vec_id,
            text=vec_data.get("text", ""),
            score=score,
            metadata=vec_data.get("metadata", {})
        ))
    
    # Sort by score and return top k
    results.sort(key=lambda x: x.score, reverse=True)
    return results[:k]

