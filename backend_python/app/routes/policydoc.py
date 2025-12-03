"""Policy document routes."""
from fastapi import APIRouter, HTTPException
from typing import List, Dict, Any
from app.clients.vectorstore import query_vectorstore
from app.clients.vectorstore.json_adapter import _json_store
from app.services.embeddings import get_embedding
from pathlib import Path
import uuid
from datetime import datetime

router = APIRouter()


@router.get("/chunks")
async def get_policy_chunks():
    """Get available policy document chunks metadata."""
    try:
        # Query with a generic query to get all chunks (or sample)
        # In a real implementation, you'd maintain a chunks index
        # For now, return metadata about available chunks
        
        # Try to get chunks by querying with a broad term
        sample_chunks = await query_vectorstore("policy document", k=10)
        
        chunks_metadata = [
            {
                "id": chunk.id,
                "title": chunk.metadata.get("title", f"Policy Section {chunk.id[:8]}"),
                "summary": chunk.text[:150] + "..." if len(chunk.text) > 150 else chunk.text,
                "score": chunk.score,
            }
            for chunk in sample_chunks
        ]
        
        return {"chunks": chunks_metadata}
    except Exception as e:
        print(f"Error fetching policy chunks: {e}")
        # Return empty list if vector store unavailable
        return {"chunks": []}


@router.post("/seed")
async def seed_policy_documents():
    """Seed policy documents from policies/company-policy.md into vectorstore."""
    try:
        # Find policy document (prioritize Python backend paths)
        possible_paths = [
            # Primary: Python backend policies directory
            Path(__file__).parent.parent.parent.parent / "backend_python" / "policies" / "company-policy.md",
            Path(__file__).parent.parent.parent.parent / "policies" / "company-policy.md",
            # Legacy: old TypeScript backend path (for migration)
            Path(__file__).parent.parent.parent.parent / "backend" / "policies" / "company-policy.md",
            Path(__file__).parent.parent.parent / "backend" / "policies" / "company-policy.md",
            Path.cwd() / "backend" / "policies" / "company-policy.md",
        ]
        
        policy_path = None
        for path in possible_paths:
            if path.exists():
                policy_path = path
                break
        
        if not policy_path:
            raise HTTPException(status_code=404, detail="Policy document not found. Expected at policies/company-policy.md or backend_python/policies/company-policy.md")
        
        chunk_count = await _seed_document(policy_path, "policy")
        
        return {
            "success": True,
            "chunks_seeded": chunk_count,
            "source": str(policy_path),
        }
    except Exception as error:
        print(f"Error seeding policy documents: {error}")
        raise HTTPException(status_code=500, detail=f"Failed to seed policy documents: {str(error)}")


@router.post("/seed-trading-terms")
async def seed_trading_terms():
    """Seed trading company terms and conditions from policies/trading-company-terms.md into vectorstore."""
    try:
        # Find trading terms document
        possible_paths = [
            Path(__file__).parent.parent.parent.parent / "backend_python" / "policies" / "trading-company-terms.md",
            Path(__file__).parent.parent.parent.parent / "policies" / "trading-company-terms.md",
            Path.cwd() / "backend_python" / "policies" / "trading-company-terms.md",
            Path.cwd() / "policies" / "trading-company-terms.md",
        ]
        
        terms_path = None
        for path in possible_paths:
            if path.exists():
                terms_path = path
                break
        
        if not terms_path:
            raise HTTPException(status_code=404, detail="Trading terms document not found. Expected at backend_python/policies/trading-company-terms.md")
        
        chunk_count = await _seed_document(terms_path, "trading_terms")
        
        return {
            "success": True,
            "chunks_seeded": chunk_count,
            "source": str(terms_path),
        }
    except Exception as error:
        print(f"Error seeding trading terms: {error}")
        raise HTTPException(status_code=500, detail=f"Failed to seed trading terms: {str(error)}")


@router.post("/seed-countries")
async def seed_countries_knowledge():
    """Seed countries knowledge from policies/countries-knowledge.md into vectorstore."""
    try:
        # Find countries knowledge document
        possible_paths = [
            Path(__file__).parent.parent.parent.parent / "backend_python" / "policies" / "countries-knowledge.md",
            Path(__file__).parent.parent.parent.parent / "policies" / "countries-knowledge.md",
            Path.cwd() / "backend_python" / "policies" / "countries-knowledge.md",
            Path.cwd() / "policies" / "countries-knowledge.md",
        ]
        
        countries_path = None
        for path in possible_paths:
            if path.exists():
                countries_path = path
                break
        
        if not countries_path:
            raise HTTPException(status_code=404, detail="Countries knowledge document not found. Expected at backend_python/policies/countries-knowledge.md")
        
        await _seed_document(countries_path, "countries")
        
        return {
            "success": True,
            "chunks_seeded": "See logs for details",
            "source": str(countries_path),
        }
    except Exception as error:
        print(f"Error seeding countries knowledge: {error}")
        raise HTTPException(status_code=500, detail=f"Failed to seed countries knowledge: {str(error)}")


async def _seed_document(doc_path: Path, doc_type: str):
    """Helper function to seed a document using heading-based chunking."""
    # Read and chunk document
    content = doc_path.read_text(encoding="utf-8")
    
    # Context-based chunking using headings as delimiters
    # Each heading (##, ###, ####, etc.) creates a new chunk boundary
    # This ensures semantic coherence - each section becomes its own chunk
    chunks = []
    current_chunk_lines = []
    current_section_title = ""
    current_section_level = 0
    
    def is_heading(line: str) -> tuple[bool, int, str]:
        """Check if line is a markdown heading and return (is_heading, level, title)."""
        line_stripped = line.strip()
        if not line_stripped.startswith("#"):
            return (False, 0, "")
        
        # Count leading # characters to determine heading level
        level = 0
        for char in line_stripped:
            if char == "#":
                level += 1
            else:
                break
        
        # Valid markdown heading levels are 1-6
        if level > 0 and level <= 6:
            # Extract title (everything after the #s and any whitespace)
            title = line_stripped[level:].strip()
            return (True, level, title)
        return (False, 0, "")
    
    # Process document line by line
    for line in content.split("\n"):
        is_heading_line, heading_level, heading_title = is_heading(line)
        
        if is_heading_line:
            # Save previous chunk if it has content
            if current_chunk_lines:
                chunk_text = "\n".join(current_chunk_lines).strip()
                # Only save chunks with meaningful content (at least 30 chars)
                # This is context-based, not size-based - we're checking for content, not enforcing a size limit
                if chunk_text and len(chunk_text) >= 30:
                    chunks.append((current_section_title, chunk_text))
            
            # Start a new chunk with this heading
            # Each heading creates a new semantic boundary
            current_section_title = heading_title
            current_section_level = heading_level
            current_chunk_lines = [line]  # Include the heading line in the chunk
        else:
            # Add content line to current chunk
            current_chunk_lines.append(line)
    
    # Save the final chunk
    if current_chunk_lines:
        chunk_text = "\n".join(current_chunk_lines).strip()
        if chunk_text and len(chunk_text) >= 30:
            chunks.append((current_section_title, chunk_text))
    
    # Generate embeddings and store
    chunk_count = 0
    for section, chunk_text in chunks:
        if len(chunk_text) < 50:  # Skip very short chunks
            continue
        
        try:
            embedding = await get_embedding(chunk_text)
            if not embedding or len(embedding) == 0:
                continue
            
            chunk_id = f"{doc_type}_{section.lower().replace(' ', '_').replace('#', '').replace('/', '_')}_{uuid.uuid4().hex[:8]}"
            
            # Initialize _vectors if needed (avoid triggering load through property)
            if _json_store._vectors is None:
                _json_store._vectors = {}
            
            # Add chunk directly to _vectors to avoid triggering load
            _json_store._vectors[chunk_id] = {
                "id": chunk_id,
                "text": chunk_text,
                "embedding": embedding,
                "metadata": {
                    "source": str(doc_path),
                    "source_name": doc_path.name,
                    "section": section,
                    "type": doc_type,
                    "seeded_at": datetime.now().isoformat(),
                },
            }
            chunk_count += 1
        except Exception as e:
            print(f"Error processing chunk '{section}': {e}")
            continue
    
    # Save to disk
    _json_store.save()
    print(f"[Seed] ✅ Seeded {chunk_count} chunks from {doc_path.name} (type: {doc_type})")
    
    return chunk_count

