#!/usr/bin/env python3
"""Quick script to seed policy documents using the backend's environment."""
import asyncio
import sys
from pathlib import Path

# Add backend_python to path
sys.path.insert(0, str(Path(__file__).parent / "backend_python"))

from app.clients.vectorstore.json_adapter import _json_store
from app.services.embeddings import get_embedding
import uuid
from datetime import datetime


async def seed_policy():
    """Seed policy documents."""
    policy_path = Path(__file__).parent / "backend" / "policies" / "company-policy.md"
    
    if not policy_path.exists():
        print(f"❌ Policy document not found at: {policy_path}")
        return
    
    print(f"📄 Reading policy document: {policy_path}")
    content = policy_path.read_text(encoding="utf-8")
    
    # Chunk by sections (## headers)
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
    
    print(f"📦 Found {len(chunks)} sections to process")
    
    # Generate embeddings and store
    chunk_count = 0
    for i, (section, chunk_text) in enumerate(chunks):
        if len(chunk_text) < 50:
            continue
        
        print(f"  Processing section {i+1}/{len(chunks)}: {section[:50]}...")
        
        try:
            embedding = await get_embedding(chunk_text)
            if not embedding or len(embedding) == 0:
                print(f"    ⚠️  Empty embedding, skipping")
                continue
            
            chunk_id = f"policy_{section.lower().replace(' ', '_').replace('#', '').replace('/', '_')[:30]}_{uuid.uuid4().hex[:8]}"
            
            _json_store.vectors[chunk_id] = {
                "id": chunk_id,
                "text": chunk_text,
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
            print(f"    ✅ Saved chunk {chunk_count}")
        except Exception as e:
            print(f"    ❌ Error: {e}")
            continue
    
    # Save to disk
    _json_store.save()
    print(f"\n✅ Successfully seeded {chunk_count} policy chunks!")


if __name__ == "__main__":
    asyncio.run(seed_policy())

