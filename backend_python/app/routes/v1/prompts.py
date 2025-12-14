"""Prompt library and versioning endpoints."""
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from typing import Optional, List
from app.db.connection import get_pool
from app.auth.roles import require_role
from datetime import datetime
import uuid

router = APIRouter()


class CreatePromptRequest(BaseModel):
    """Request to create a prompt."""
    name: str
    content: str
    version: Optional[int] = None
    active: Optional[bool] = False


class UpdatePromptRequest(BaseModel):
    """Request to update a prompt."""
    name: Optional[str] = None
    content: Optional[str] = None
    active: Optional[bool] = None


class PromptResponse(BaseModel):
    """Prompt response model."""
    id: str
    name: str
    content: str
    version: int
    active: bool
    created_at: str
    updated_at: str


@router.post("", response_model=PromptResponse)
async def create_prompt(
    request: CreatePromptRequest,
    current_user: dict = Depends(require_role("admin")),
):
    """Create a new prompt version."""
    try:
        pool = await get_pool()
        async with pool.acquire() as conn:
            # Determine version
            if request.version:
                version = request.version
            else:
                # Get max version for this name
                max_version_row = await conn.fetchrow(
                    "SELECT MAX(version) as max_version FROM prompts WHERE name = $1",
                    request.name,
                )
                version = (max_version_row["max_version"] or 0) + 1
            
            # If setting as active, deactivate other versions
            if request.active:
                await conn.execute(
                    "UPDATE prompts SET active = false WHERE name = $1",
                    request.name,
                )
            
            prompt_id = uuid.uuid4()
            now = datetime.now()
            
            await conn.execute(
                """
                INSERT INTO prompts (id, name, content, version, active, created_at, updated_at)
                VALUES ($1, $2, $3, $4, $5, $6, $7)
                """,
                prompt_id,
                request.name,
                request.content,
                version,
                request.active,
                now,
                now,
            )
            
            return PromptResponse(
                id=str(prompt_id),
                name=request.name,
                content=request.content,
                version=version,
                active=request.active,
                created_at=now.isoformat(),
                updated_at=now.isoformat(),
            )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to create prompt: {str(e)}")


@router.get("", response_model=List[PromptResponse])
async def list_prompts(
    name: Optional[str] = None,
    active_only: Optional[bool] = None,
):
    """List all prompts, optionally filtered by name or active status."""
    try:
        pool = await get_pool()
        async with pool.acquire() as conn:
            query = "SELECT * FROM prompts WHERE 1=1"
            params = []
            
            if name:
                query += " AND name = $" + str(len(params) + 1)
                params.append(name)
            
            if active_only:
                query += " AND active = $" + str(len(params) + 1)
                params.append(True)
            
            query += " ORDER BY name, version DESC"
            
            rows = await conn.fetch(query, *params)
            
            return [
                PromptResponse(
                    id=str(row["id"]),
                    name=row["name"],
                    content=row["content"],
                    version=row["version"],
                    active=row["active"],
                    created_at=row["created_at"].isoformat(),
                    updated_at=row["updated_at"].isoformat(),
                )
                for row in rows
            ]
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to list prompts: {str(e)}")


@router.get("/{prompt_id}", response_model=PromptResponse)
async def get_prompt(prompt_id: str):
    """Get a specific prompt by ID."""
    try:
        pool = await get_pool()
        async with pool.acquire() as conn:
            row = await conn.fetchrow(
                "SELECT * FROM prompts WHERE id = $1",
                uuid.UUID(prompt_id),
            )
            
            if not row:
                raise HTTPException(status_code=404, detail="Prompt not found")
            
            return PromptResponse(
                id=str(row["id"]),
                name=row["name"],
                content=row["content"],
                version=row["version"],
                active=row["active"],
                created_at=row["created_at"].isoformat(),
                updated_at=row["updated_at"].isoformat(),
            )
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid prompt ID")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get prompt: {str(e)}")


@router.patch("/{prompt_id}", response_model=PromptResponse)
async def update_prompt(
    prompt_id: str,
    request: UpdatePromptRequest,
    current_user: dict = Depends(require_role("admin")),
):
    """Update a prompt."""
    try:
        pool = await get_pool()
        async with pool.acquire() as conn:
            # Check prompt exists
            existing = await conn.fetchrow(
                "SELECT * FROM prompts WHERE id = $1",
                uuid.UUID(prompt_id),
            )
            if not existing:
                raise HTTPException(status_code=404, detail="Prompt not found")
            
            # Build update query
            updates = []
            params = []
            
            if request.name is not None:
                updates.append(f"name = ${len(params) + 1}")
                params.append(request.name)
            
            if request.content is not None:
                updates.append(f"content = ${len(params) + 1}")
                params.append(request.content)
            
            if request.active is not None:
                updates.append(f"active = ${len(params) + 1}")
                params.append(request.active)
                
                # If activating, deactivate other versions of same name
                if request.active:
                    await conn.execute(
                        "UPDATE prompts SET active = false WHERE name = $1 AND id != $2",
                        existing["name"],
                        uuid.UUID(prompt_id),
                    )
            
            if not updates:
                # No updates, return existing
                return PromptResponse(
                    id=str(existing["id"]),
                    name=existing["name"],
                    content=existing["content"],
                    version=existing["version"],
                    active=existing["active"],
                    created_at=existing["created_at"].isoformat(),
                    updated_at=existing["updated_at"].isoformat(),
                )
            
            updates.append(f"updated_at = ${len(params) + 1}")
            params.append(datetime.now())
            params.append(uuid.UUID(prompt_id))
            
            query = f"UPDATE prompts SET {', '.join(updates)} WHERE id = ${len(params)}"
            await conn.execute(query, *params)
            
            # Fetch updated prompt
            updated = await conn.fetchrow(
                "SELECT * FROM prompts WHERE id = $1",
                uuid.UUID(prompt_id),
            )
            
            return PromptResponse(
                id=str(updated["id"]),
                name=updated["name"],
                content=updated["content"],
                version=updated["version"],
                active=updated["active"],
                created_at=updated["created_at"].isoformat(),
                updated_at=updated["updated_at"].isoformat(),
            )
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid prompt ID")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to update prompt: {str(e)}")


@router.delete("/{prompt_id}")
async def delete_prompt(
    prompt_id: str,
    current_user: dict = Depends(require_role("admin")),
):
    """Delete a prompt."""
    try:
        pool = await get_pool()
        async with pool.acquire() as conn:
            result = await conn.execute(
                "DELETE FROM prompts WHERE id = $1",
                uuid.UUID(prompt_id),
            )
            
            if result == "DELETE 0":
                raise HTTPException(status_code=404, detail="Prompt not found")
            
            return {"success": True, "message": "Prompt deleted"}
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid prompt ID")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to delete prompt: {str(e)}")


@router.get("/active", response_model=Optional[PromptResponse])
async def get_active_prompt(name: Optional[str] = None):
    """Get the active prompt (optionally filtered by name)."""
    try:
        pool = await get_pool()
        async with pool.acquire() as conn:
            if name:
                row = await conn.fetchrow(
                    "SELECT * FROM prompts WHERE name = $1 AND active = true ORDER BY version DESC LIMIT 1",
                    name,
                )
            else:
                # Get most recent active prompt
                row = await conn.fetchrow(
                    "SELECT * FROM prompts WHERE active = true ORDER BY created_at DESC LIMIT 1",
                )
            
            if not row:
                return None
            
            return PromptResponse(
                id=str(row["id"]),
                name=row["name"],
                content=row["content"],
                version=row["version"],
                active=row["active"],
                created_at=row["created_at"].isoformat(),
                updated_at=row["updated_at"].isoformat(),
            )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get active prompt: {str(e)}")
