#!/usr/bin/env python3
"""
Standalone script to seed policy documents.
Uses the backend's vectorstore and embeddings directly.
"""
import asyncio
import sys
import os
from pathlib import Path

# Add backend_python to path
backend_python = Path(__file__).parent / "backend_python"
sys.path.insert(0, str(backend_python))

# Load .env manually
env_file = Path(__file__).parent / ".env"
if env_file.exists():
    with open(env_file, "r") as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                key, value = line.split("=", 1)
                os.environ[key.strip()] = value.strip().strip('"').strip("'")

# Now import backend modules
from app.clients.vectorstore.json_adapter import JSONVectorStore
from app.services.embeddings import get_embedding
import uuid
from datetime import datetime

async def seed():
    """Seed policy documents."""
    # Initialize vectorstore
    store = JSONVectorStore()
    
    # Find policy document
    policy_path = Path(__file__).parent / "backend" / "policies" / "company-policy.md"
    if not policy_path.exists():
        print(f"❌ Policy not found: {policy_path}")
        return
    
    print(f"📄 Reading: {policy_path}")
    content = policy_path.read_text(encoding="utf-8")
    
    # Chunk by sections
    chunks = []
    current_chunk = ""
    current_section = ""
    
    for line in content.split("\n"):
        if line.startswith("##"):
            if current_chunk:
                chunks.append((current_section, current_chunk.strip()))
            current_section = line.replace("##", "").strip()
            current_chunk = line + "\n"
        else:
            current_chunk += line + "\n"
    
    if current_chunk:
        chunks.append((current_section, current_chunk.strip()))
    
    print(f"📦 Processing {len(chunks)} sections...")
    
    # Process chunks
    chunk_count = 0
    for i, (section, text) in enumerate(chunks):
        if len(text) < 50:
            continue
        
        print(f"  [{i+1}/{len(chunks)}] {section[:40]}...")
        
        try:
            embedding = await get_embedding(text)
            if not embedding:
                print(f"    ⚠️  No embedding")
                continue
            
            chunk_id = f"policy_{section.lower().replace(' ', '_').replace('#', '')[:30]}_{uuid.uuid4().hex[:8]}"
            
            store.vectors[chunk_id] = {
                "id": chunk_id,
                "text": text,
                "embedding": embedding,
                "metadata": {
                    "source": str(policy_path),
                    "source_name": policy_path.name,
                    "section": section,
                    "type": "kb",
                    "seeded_at": datetime.now().isoformat(),
                },
            }
            chunk_count += 1
            print(f"    ✅ Saved")
        except Exception as e:
            print(f"    ❌ Error: {e}")
    
    # Save
    store.save()
    print(f"\n✅ Seeded {chunk_count} chunks to {store.file_path}")

if __name__ == "__main__":
    asyncio.run(seed())

