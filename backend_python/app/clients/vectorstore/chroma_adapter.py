"""Chroma vector store adapter."""
import os
import httpx
from typing import List
from app.clients.vectorstore import VectorQueryResult
from app.services.embeddings import get_embedding


CHROMA_BASE_URL = os.getenv("CHROMA_BASE_URL", "http://localhost:8000")
COLLECTION_NAME = os.getenv("CHROMA_COLLECTION", "policy_documents")


async def check_chroma_health() -> bool:
    """Check if Chroma is available."""
    try:
        async with httpx.AsyncClient(timeout=2.0) as client:
            response = await client.get(f"{CHROMA_BASE_URL}/api/v1/heartbeat")
            return response.status_code == 200
    except Exception:
        return False


async def ensure_collection() -> str:
    """Ensure Chroma collection exists, return collection ID."""
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            # Try to get existing collection
            response = await client.get(
                f"{CHROMA_BASE_URL}/api/v1/collections",
                params={"name": COLLECTION_NAME}
            )
            
            if response.status_code == 200:
                collections = response.json()
                if collections and len(collections) > 0:
                    return collections[0]["id"]
            
            # Create collection if it doesn't exist
            create_response = await client.post(
                f"{CHROMA_BASE_URL}/api/v1/collections",
                json={"name": COLLECTION_NAME}
            )
            
            if create_response.status_code == 200:
                return create_response.json()["id"]
            
            raise Exception(f"Failed to create collection: {create_response.status_code}")
    except Exception as e:
        print(f"[Chroma] Collection error: {e}")
        raise


async def query_chroma(query_text: str, k: int = 3) -> List[VectorQueryResult]:
    """Query Chroma vector store."""
    try:
        coll_id = await ensure_collection()
        query_embedding = await get_embedding(query_text)
        
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.post(
                f"{CHROMA_BASE_URL}/api/v1/collections/{coll_id}/query",
                json={
                    "query_embeddings": [query_embedding],
                    "n_results": k,
                }
            )
            
            if response.status_code != 200:
                raise Exception(f"Chroma query failed: {response.status_code}")
            
            data = response.json()
            results = []
            
            if data.get("ids") and data["ids"][0]:
                for i in range(len(data["ids"][0])):
                    results.append(VectorQueryResult(
                        id=data["ids"][0][i],
                        text=data.get("documents", [[]])[0][i] if data.get("documents") else "",
                        score=1.0 - (data.get("distances", [[]])[0][i] if data.get("distances") else 0.0),
                        metadata=data.get("metadatas", [[]])[0][i] if data.get("metadatas") else {}
                    ))
            
            return results
    except Exception as e:
        print(f"[Chroma] Query error: {e}")
        raise

