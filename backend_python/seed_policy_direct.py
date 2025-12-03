#!/usr/bin/env python3
"""Direct script to seed policy documents - runs in backend environment."""
import asyncio
import sys
from pathlib import Path

# Ensure we're in the right directory
backend_python = Path(__file__).parent
sys.path.insert(0, str(backend_python))

# Load environment variables from .env file manually
import os
env_file = backend_python.parent / ".env"
if env_file.exists():
    with open(env_file, "r") as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                key, value = line.split("=", 1)
                os.environ[key.strip()] = value.strip().strip('"').strip("'")

from app.clients.vectorstore.json_adapter import _json_store
from app.services.embeddings import get_embedding
import uuid
from datetime import datetime


async def seed_policy():
    """Seed policy documents."""
    # Find policy document
    possible_paths = [
        backend_python.parent / "backend" / "policies" / "company-policy.md",
        Path.cwd() / "backend" / "policies" / "company-policy.md",
    ]
    
    policy_path = None
    for path in possible_paths:
        if path.exists():
            policy_path = path
            break
    
    if not policy_path:
        print(f"❌ Policy document not found. Tried: {possible_paths}")
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
        
        section_name = section[:50] if section else f"Section {i+1}"
        print(f"  [{i+1}/{len(chunks)}] Processing: {section_name}...")
        
        try:
            embedding = await get_embedding(chunk_text)
            if not embedding or len(embedding) == 0:
                print(f"    ⚠️  Empty embedding, skipping")
                continue
            
            # Create safe ID
            safe_section = section.lower().replace(' ', '_').replace('#', '').replace('/', '_').replace('\\', '_')[:30]
            chunk_id = f"policy_{safe_section}_{uuid.uuid4().hex[:8]}"
            
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
            import traceback
            traceback.print_exc()
            continue
    
    # Save to disk
    print(f"\n💾 Saving to {_json_store.file_path}...")
    _json_store.save()
    print(f"✅ Successfully seeded {chunk_count} policy chunks!")
    print(f"📁 Vectorstore file: {_json_store.file_path}")


if __name__ == "__main__":
    asyncio.run(seed_policy())

