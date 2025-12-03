"""JSON-based vector store adapter (fallback when Chroma unavailable)."""
import json
import os
from pathlib import Path
from typing import List, Dict, Any
from app.clients.vectorstore import VectorQueryResult
from app.services.embeddings import get_embedding


class JSONVectorStore:
    """Simple JSON-based vector store for RAG. Always loads fresh from file."""
    
    def __init__(self):
        # Try multiple paths for storage (prioritize Python backend paths)
        # __file__ is at: backend_python/app/clients/vectorstore/json_adapter.py
        json_adapter_path = Path(__file__).resolve()
        repo_root = json_adapter_path.parent.parent.parent.parent
        
        # Handle case where path might have double backend_python
        # Normalize to single backend_python level
        path_parts = list(repo_root.parts)
        if path_parts.count("backend_python") > 1:
            # Remove duplicate backend_python entries, keep only the last one
            normalized_parts = []
            seen_backend_python = False
            for part in path_parts:
                if part == "backend_python":
                    if not seen_backend_python:
                        normalized_parts.append(part)
                        seen_backend_python = True
                    # Skip duplicate
                else:
                    normalized_parts.append(part)
            backend_python_root = Path(*normalized_parts)
        elif repo_root.name == "backend_python":
            backend_python_root = repo_root
        else:
            # Try to find backend_python in parent
            backend_python_root = repo_root.parent / "backend_python" if (repo_root.parent / "backend_python").exists() else repo_root
        
        # Absolute path to ensure consistency - prioritize known correct path
        # Direct absolute path (most reliable - check this first)
        correct_absolute_path = Path("/Users/nishantsangwan/Documents/Repos/AI_Assistant/backend_python/storage/vectors.json")
        
        absolute_paths = [
            # Primary: Direct absolute path (most reliable)
            correct_absolute_path,
            # Secondary: Python backend storage directory (normalized path)
            backend_python_root / "storage" / "vectors.json",
            # Fallback: repo root storage
            repo_root.parent / "storage" / "vectors.json",
        ]
        
        # Also try relative paths (resolve to absolute)
        relative_paths = [
            (Path.cwd() / "backend_python" / "storage" / "vectors.json").resolve(),
            (Path.cwd() / "storage" / "vectors.json").resolve(),
        ]
        
        possible_paths = absolute_paths + relative_paths
        
        # If correct path doesn't exist but wrong path does, copy it
        wrong_path = Path("/Users/nishantsangwan/Documents/Repos/AI_Assistant/backend_python/backend_python/storage/vectors.json")
        if wrong_path.exists() and not correct_absolute_path.exists():
            try:
                correct_absolute_path.parent.mkdir(parents=True, exist_ok=True)
                import shutil
                shutil.copy2(wrong_path, correct_absolute_path)
                print(f"[VectorStore] ✅ Copied vectors from wrong path to correct path")
            except Exception as e:
                print(f"[VectorStore] ⚠️ Could not copy vectors file: {e}")
        
        self.file_path = None
        for path in possible_paths:
            # Resolve to absolute path and check if file exists
            try:
                # All paths should already be absolute after resolve(), but ensure it
                abs_path = path.resolve() if hasattr(path, 'resolve') else Path(path).resolve()
                if abs_path.exists() and abs_path.is_file():
                    self.file_path = abs_path
                    print(f"[VectorStore] ✅ Found vectors file at: {self.file_path}")
                    break
                else:
                    print(f"[VectorStore] Path exists check: {abs_path} -> exists={abs_path.exists()}, is_file={abs_path.is_file() if abs_path.exists() else 'N/A'}")
            except (OSError, RuntimeError) as e:
                # Skip paths that can't be resolved (e.g., symlink issues)
                print(f"[VectorStore] ⚠️ Skipping path {path}: {e}")
                continue
        
        if not self.file_path:
            # Create default path in Python backend (use absolute path)
            default_path = repo_root / "storage" / "vectors.json"
            default_path.parent.mkdir(parents=True, exist_ok=True)
            self.file_path = default_path.resolve()
            print(f"[VectorStore] Using default path: {self.file_path}")
        
        # Don't load vectors in __init__ - always load fresh when accessed
        self._vectors: Dict[str, Dict[str, Any]] = None
        self._last_load_time = 0
    
    def load(self, force: bool = True):
        """Load vectors from JSON file. Always reloads fresh from disk."""
        try:
            print(f"[VectorStore] Loading fresh from: {self.file_path}")
            if not self.file_path.exists():
                print(f"[VectorStore] File does not exist: {self.file_path}")
                self._vectors = {}
                return
            
            with open(self.file_path, "r", encoding="utf-8") as f:
                stored = json.load(f)
                print(f"[VectorStore] Parsed JSON: type={type(stored)}, length={len(stored) if isinstance(stored, (list, dict)) else 'N/A'}")
                
                if isinstance(stored, list):
                    self._vectors = {v["id"]: v for v in stored}
                else:
                    self._vectors = stored
                
                import time
                self._last_load_time = time.time()
                print(f"[VectorStore] ✅ Loaded {len(self._vectors)} vectors from JSON at {self.file_path}")
        except Exception as e:
            print(f"[VectorStore] ❌ Could not load JSON store: {e}")
            import traceback
            traceback.print_exc()
            self._vectors = {}
    
    @property
    def vectors(self) -> Dict[str, Dict[str, Any]]:
        """Get vectors, always loading fresh from file."""
        # Always reload from file to ensure we have the latest data
        self.load(force=True)
        return self._vectors if self._vectors is not None else {}
    
    def save(self):
        """Save vectors to JSON file."""
        try:
            # Ensure directory exists
            self.file_path.parent.mkdir(parents=True, exist_ok=True)
            # Use _vectors directly to avoid triggering load() which would overwrite with empty file
            vectors_to_save = self._vectors if self._vectors is not None else {}
            with open(self.file_path, "w", encoding="utf-8") as f:
                json.dump(list(vectors_to_save.values()), f, indent=2)
            print(f"[VectorStore] ✅ Saved {len(vectors_to_save)} vectors to {self.file_path}")
        except Exception as e:
            print(f"[VectorStore] ❌ Error saving JSON store: {e}")
            import traceback
            traceback.print_exc()
    
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
    """Query JSON vector store. Always loads fresh vectors from file."""
    # Always reload fresh from file on every query
    _json_store.load(force=True)
    
    vectors = _json_store.vectors
    if len(vectors) == 0:
        print(f"[VectorStore] Warning: Vector store is empty. File path: {_json_store.file_path}, exists: {_json_store.file_path.exists()}")
        return []
    
    # Get embedding for query
    try:
        query_embedding = await get_embedding(query_text)
        
        if not query_embedding or len(query_embedding) == 0:
            print("[VectorStore] Warning: Empty embedding generated for query")
            return []
    except Exception as e:
        print(f"[VectorStore] Error generating query embedding: {e}")
        return []
    
    # Calculate similarities
    results = []
    vectors = _json_store.vectors  # Get fresh vectors
    for vec_id, vec_data in vectors.items():
        if "embedding" not in vec_data:
            continue
        
        try:
            score = _json_store.cosine_similarity(query_embedding, vec_data["embedding"])
            results.append(VectorQueryResult(
                id=vec_id,
                text=vec_data.get("text", ""),
                score=score,
                metadata=vec_data.get("metadata", {})
            ))
        except Exception as e:
            print(f"[VectorStore] Error calculating similarity for {vec_id}: {e}")
            continue
    
    # Sort by score and return top k
    results.sort(key=lambda x: x.score, reverse=True)
    filtered_results = [r for r in results[:k] if r.score > 0.1]  # Filter very low scores
    
    if len(filtered_results) == 0 and len(results) > 0:
        # Return top result even if score is low (might be relevant)
        return results[:1]
    
    return filtered_results

