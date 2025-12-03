"""Prompt library endpoints."""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional
from datetime import datetime
from app.db.connection import get_pool
import uuid

router = APIRouter()


class CreatePromptRequest(BaseModel):
    """Request to create a prompt."""
    name: str
    content: str
    version: Optional[str] = None


class UpdatePromptRequest(BaseModel):
    """Request to update a prompt."""
    name: Optional[str] = None
    content: Optional[str] = None
    active: Optional[bool] = None


@router.post("")
async def create_prompt(request: CreatePromptRequest):
    """Create a new prompt version."""
    try:
        pool = await get_pool()
        async with pool.acquire() as conn:
            prompt_id = str(uuid.uuid4())
            version = request.version or "1.0.0"
            
            await conn.execute(
                """
                INSERT INTO prompts (id, name, content, version, active, created_at)
                VALUES ($1, $2, $3, $4, $5, $6)
                """,
                prompt_id,
                request.name,
                request.content,
                version,
                True,  # New prompts are active by default
                datetime.now().isoformat(),
            )
            
            return {
                "id": prompt_id,
                "name": request.name,
                "content": request.content,
                "version": version,
                "active": True,
            }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to create prompt: {str(e)}")


@router.get("")
async def list_prompts():
    """List all prompts."""
    try:
        pool = await get_pool()
        async with pool.acquire() as conn:
            rows = await conn.fetch("SELECT * FROM prompts ORDER BY created_at DESC")
            return [dict(row) for row in rows]
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to list prompts: {str(e)}")


@router.get("/active")
async def get_active_prompt(name: Optional[str] = None):
    """Get active prompt by name (or latest if name not specified)."""
    try:
        pool = await get_pool()
        async with pool.acquire() as conn:
            if name:
                row = await conn.fetchrow(
                    "SELECT * FROM prompts WHERE name = $1 AND active = true ORDER BY created_at DESC LIMIT 1",
                    name,
                )
            else:
                row = await conn.fetchrow(
                    "SELECT * FROM prompts WHERE active = true ORDER BY created_at DESC LIMIT 1"
                )
            
            if not row:
                raise HTTPException(status_code=404, detail="No active prompt found")
            
            return dict(row)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get active prompt: {str(e)}")


@router.get("/{prompt_id}")
async def get_prompt(prompt_id: str):
    """Get prompt by ID."""
    try:
        pool = await get_pool()
        async with pool.acquire() as conn:
            row = await conn.fetchrow("SELECT * FROM prompts WHERE id = $1", prompt_id)
            if not row:
                raise HTTPException(status_code=404, detail="Prompt not found")
            return dict(row)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get prompt: {str(e)}")


@router.put("/{prompt_id}")
async def update_prompt(prompt_id: str, request: UpdatePromptRequest):
    """Update a prompt."""
    try:
        pool = await get_pool()
        async with pool.acquire() as conn:
            updates = []
            values = []
            param_num = 1
            
            if request.name is not None:
                updates.append(f"name = ${param_num}")
                values.append(request.name)
                param_num += 1
            
            if request.content is not None:
                updates.append(f"content = ${param_num}")
                values.append(request.content)
                param_num += 1
            
            if request.active is not None:
                updates.append(f"active = ${param_num}")
                values.append(request.active)
                param_num += 1
            
            if not updates:
                raise HTTPException(status_code=400, detail="No fields to update")
            
            values.append(prompt_id)
            query = f"UPDATE prompts SET {', '.join(updates)} WHERE id = ${param_num}"
            
            result = await conn.execute(query, *values)
            if result == "UPDATE 0":
                raise HTTPException(status_code=404, detail="Prompt not found")
            
            # Return updated prompt
            row = await conn.fetchrow("SELECT * FROM prompts WHERE id = $1", prompt_id)
            return dict(row)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to update prompt: {str(e)}")


@router.delete("/{prompt_id}")
async def delete_prompt(prompt_id: str):
    """Delete a prompt."""
    try:
        pool = await get_pool()
        async with pool.acquire() as conn:
            result = await conn.execute("DELETE FROM prompts WHERE id = $1", prompt_id)
            if result == "DELETE 0":
                raise HTTPException(status_code=404, detail="Prompt not found")
            return {"success": True}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to delete prompt: {str(e)}")

