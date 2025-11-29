#!/usr/bin/env python3
"""
Seed policy documents into vector store.
Chunks documents, generates embeddings, and upserts to vectorstore.

Usage:
    python scripts/seed_policy_docs.py [policy_docs/*.md]
    python scripts/seed_policy_docs.py backend/policies/company-policy.md
"""
import asyncio
import sys
import os
from pathlib import Path
from typing import List, Dict, Any
import uuid
from datetime import datetime

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.clients.vectorstore.json_adapter import _json_store
from app.services.embeddings import get_embedding


def chunk_text(text: str, chunk_size: int = 1024, overlap: int = 50) -> List[str]:
    """
    Split text into chunks with overlap.
    
    Args:
        text: Text to chunk
        chunk_size: Target chunk size in characters
        overlap: Overlap between chunks in characters
    
    Returns:
        List of text chunks
    """
    if len(text) <= chunk_size:
        return [text]
    
    chunks = []
    start = 0
    
    while start < len(text):
        end = start + chunk_size
        
        # Try to break at sentence boundary
        if end < len(text):
            # Look for sentence endings near the end
            for punct in ['. ', '.\n', '! ', '!\n', '? ', '?\n']:
                last_punct = text.rfind(punct, start, end)
                if last_punct > start:
                    end = last_punct + len(punct)
                    break
        
        chunk = text[start:end].strip()
        if chunk:
            chunks.append(chunk)
        
        # Move start forward with overlap
        start = end - overlap
        if start >= len(text):
            break
    
    return chunks


async def seed_policy_document(file_path: Path) -> int:
    """
    Seed a single policy document into vector store.
    
    Returns:
        Number of chunks created
    """
    print(f"[Seed] Processing: {file_path}")
    
    if not file_path.exists():
        print(f"[Seed] Error: File not found: {file_path}")
        return 0
    
    # Read document
    try:
        content = file_path.read_text(encoding="utf-8")
    except Exception as e:
        print(f"[Seed] Error reading file: {e}")
        return 0
    
    if not content.strip():
        print(f"[Seed] Warning: File is empty: {file_path}")
        return 0
    
    # Chunk document
    chunks = chunk_text(content, chunk_size=1024, overlap=50)
    print(f"[Seed] Created {len(chunks)} chunks from {file_path.name}")
    
    # Generate embeddings and upsert
    chunk_count = 0
    for i, chunk_text_content in enumerate(chunks):
        try:
            # Generate embedding
            embedding = await get_embedding(chunk_text_content)
            
            if not embedding or len(embedding) == 0:
                print(f"[Seed] Warning: Empty embedding for chunk {i+1}")
                continue
            
            # Create chunk ID
            chunk_id = f"{file_path.stem}_chunk_{i+1}_{uuid.uuid4().hex[:8]}"
            
            # Prepare metadata
            metadata = {
                "source": str(file_path),
                "source_name": file_path.name,
                "chunk_index": i + 1,
                "total_chunks": len(chunks),
                "title": f"{file_path.stem} - Section {i+1}",
                "seeded_at": datetime.now().isoformat(),
            }
            
            # Upsert to JSON store
            _json_store.vectors[chunk_id] = {
                "id": chunk_id,
                "text": chunk_text_content,
                "embedding": embedding,
                "metadata": metadata,
            }
            
            chunk_count += 1
            
            if (i + 1) % 10 == 0:
                print(f"[Seed] Processed {i+1}/{len(chunks)} chunks...")
        
        except Exception as e:
            print(f"[Seed] Error processing chunk {i+1}: {e}")
            continue
    
    # Save to disk
    try:
        _json_store.save()
        print(f"[Seed] ✅ Saved {chunk_count} chunks to vector store")
    except Exception as e:
        print(f"[Seed] Error saving vector store: {e}")
        return 0
    
    return chunk_count


async def main():
    """Main entry point."""
    # Default to company-policy.md if no args
    if len(sys.argv) > 1:
        file_paths = [Path(p) for p in sys.argv[1:]]
    else:
        # Try to find policy documents
        possible_paths = [
            Path(__file__).parent.parent.parent / "backend" / "policies" / "company-policy.md",
            Path(__file__).parent.parent / "backend" / "policies" / "company-policy.md",
            Path.cwd() / "backend" / "policies" / "company-policy.md",
            Path.cwd() / "policies" / "company-policy.md",
        ]
        
        file_paths = []
        for path in possible_paths:
            if path.exists():
                file_paths.append(path)
                break
        
        if not file_paths:
            print("[Seed] Error: No policy documents found. Please provide path(s) as arguments.")
            print("[Seed] Usage: python scripts/seed_policy_docs.py [policy_docs/*.md]")
            sys.exit(1)
    
    total_chunks = 0
    for file_path in file_paths:
        chunks = await seed_policy_document(file_path)
        total_chunks += chunks
    
    # Update metadata
    metadata_path = Path(__file__).parent.parent / "backend_python" / "storage" / "vector_metadata.json"
    metadata_path.parent.mkdir(parents=True, exist_ok=True)
    
    metadata = {
        "last_seeded_at": datetime.now().isoformat(),
        "total_chunks": total_chunks,
        "sources": [str(p) for p in file_paths],
    }
    
    import json
    with open(metadata_path, "w") as f:
        json.dump(metadata, f, indent=2)
    
    print(f"\n[Seed] ✅ Complete! Seeded {total_chunks} chunks from {len(file_paths)} file(s)")
    print(f"[Seed] Metadata saved to: {metadata_path}")


if __name__ == "__main__":
    asyncio.run(main())

