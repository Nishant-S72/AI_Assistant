"""Admin routes."""
from fastapi import APIRouter, HTTPException, Depends, Query, Header
from typing import Optional
from app.db.connection import get_pool
import uuid
import json
from datetime import datetime, timedelta

router = APIRouter()


async def require_auth(
    authorization: Optional[str] = Header(None, alias="x-demo-token"),
    token: Optional[str] = Query(None)
):
    """Auth middleware - requires DEMO_SEED_TOKEN or ADMIN_API_KEY."""
    import os
    
    # Support both Header and Query token
    auth_token = None
    if authorization:
        # Remove "Bearer " prefix if present
        auth_token = authorization.replace("Bearer ", "") if authorization.startswith("Bearer ") else authorization
    elif token:
        auth_token = token
    
    expected_token = os.getenv("DEMO_SEED_TOKEN") or os.getenv("ADMIN_API_KEY") or "changeme"

    if not auth_token or auth_token != expected_token:
        raise HTTPException(status_code=401, detail="Unauthorized. Provide x-demo-token header or token query param.")

    return auth_token


@router.get("/audit")
async def get_audit_logs(
    limit: int = Query(50),
    offset: int = Query(0),
    _: str = Depends(require_auth),
):
    """Get audit logs."""
    try:
        pool = await get_pool()
        async with pool.acquire() as conn:
            rows = await conn.fetch(
                """
                SELECT 
                    id,
                    type,
                    correlation_id,
                    request_path,
                    user_id,
                    prompt_ref,
                    retrieved_ids,
                    raw_model_response,
                    final_text,
                    latency_ms,
                    payload,
                    created_at
                FROM events
                ORDER BY created_at DESC
                LIMIT $1 OFFSET $2
                """,
                limit,
                offset,
            )

            total_row = await conn.fetchrow("SELECT COUNT(*) as total FROM events")
            total = int(total_row["total"]) if total_row else 0

            return {
                "events": [dict(row) for row in rows],
                "total": total,
                "limit": limit,
                "offset": offset,
            }
    except Exception as error:
        print(f"Error fetching audit logs: {error}")
        raise HTTPException(status_code=500, detail="Failed to fetch audit logs")


@router.get("/metrics")
async def get_metrics(_: str = Depends(require_auth)):
    """Get metrics."""
    try:
        pool = await get_pool()
        async with pool.acquire() as conn:
            # Suggestions generated
            suggestions_row = await conn.fetchrow("SELECT COUNT(*) as count FROM suggestions")
            suggestions_generated = int(suggestions_row["count"]) if suggestions_row else 0

            # Acceptance rate
            accepted_row = await conn.fetchrow(
                """
                SELECT COUNT(*) as count 
                FROM suggestions 
                WHERE final_text IS NOT NULL 
                AND final_text = model_response 
                AND edited = false
                """
            )
            accepted = int(accepted_row["count"]) if accepted_row else 0
            acceptance_rate = accepted / suggestions_generated if suggestions_generated > 0 else 0

            # Average latency
            latency_row = await conn.fetchrow(
                """
                SELECT AVG(latency_ms) as avg_latency 
                FROM events 
                WHERE latency_ms IS NOT NULL 
                AND type = 'suggestion_generated'
                """
            )
            avg_latency = (
                round(float(latency_row["avg_latency"])) if latency_row and latency_row["avg_latency"] else None
            )

            # Messages sent
            sent_row = await conn.fetchrow("SELECT COUNT(*) as count FROM events WHERE type = 'message_sent'")
            messages_sent = int(sent_row["count"]) if sent_row else 0

            return {
                "suggestionsGenerated": suggestions_generated,
                "acceptanceRate": round(acceptance_rate * 100) / 100,
                "avgLatencyMs": avg_latency,
                "messagesSent": messages_sent,
            }
    except Exception as error:
        print(f"Error fetching metrics: {error}")
        raise HTTPException(status_code=500, detail="Failed to fetch metrics")


# Test mail chains for RAG testing
TEST_CHAINS = [
    {
        "contact": {
            "name": "Maria Rodriguez",
            "email": "maria.rodriguez@techcorp.com",
            "company": "TechCorp Solutions",
            "tags": [],  # Will be AI-generated from chat history
            "tone_pref": "formal"
        },
        "thread": [
            {
                "sender": "contact",
                "body": "Hello, I'm interested in learning more about your payment terms for large orders. What are the standard payment methods you accept?",
                "created_at": datetime.now() - timedelta(days=2)
            }
        ],
        "description": "Payment terms question - should retrieve trading terms"
    },
    {
        "contact": {
            "name": "David Kim",
            "email": "david.kim@globaltrading.com",
            "company": "Global Trading Partners",
            "tags": [],  # Will be AI-generated from chat history
            "tone_pref": "warm"
        },
        "thread": [
            {
                "sender": "contact",
                "body": "Hi, I need to understand your return policy. What happens if I receive defective products?",
                "created_at": datetime.now() - timedelta(days=1)
            }
        ],
        "description": "Return policy question - should retrieve trading terms"
    },
    {
        "contact": {
            "name": "Sarah Johnson",
            "email": "sarah.j@importexport.com",
            "company": "Import Export Inc",
            "tags": [],  # Will be AI-generated from chat history
            "tone_pref": "crisp"
        },
        "thread": [
            {
                "sender": "contact",
                "body": "What shipping methods do you offer and what are the typical delivery times?",
                "created_at": datetime.now() - timedelta(hours=12)
            }
        ],
        "description": "Shipping methods question - should retrieve trading terms"
    },
    {
        "contact": {
            "name": "James Wilson",
            "email": "james.w@supplychain.com",
            "company": "Supply Chain Solutions",
            "tags": [],  # Will be AI-generated from chat history
            "tone_pref": "warm"
        },
        "thread": [
            {
                "sender": "contact",
                "body": "I'm placing a large order. What are the minimum order quantities for industrial equipment?",
                "created_at": datetime.now() - timedelta(hours=6)
            }
        ],
        "description": "MOQ question - should retrieve trading terms"
    },
    {
        "contact": {
            "name": "Lisa Chen",
            "email": "lisa.chen@international.com",
            "company": "International Trading Co",
            "tags": [],  # Will be AI-generated from chat history
            "tone_pref": "formal"
        },
        "thread": [
            {
                "sender": "contact",
                "body": "Can you explain what Incoterms you support? I need to understand the shipping terms for our international orders.",
                "created_at": datetime.now() - timedelta(hours=3)
            }
        ],
        "description": "Incoterms question - should retrieve trading terms"
    },
    {
        "contact": {
            "name": "Robert Martinez",
            "email": "robert.m@manufacturing.com",
            "company": "Manufacturing Partners LLC",
            "tags": [],  # Will be AI-generated from chat history
            "tone_pref": "warm"
        },
        "thread": [
            {
                "sender": "contact",
                "body": "What is your warranty policy? How long is the warranty period for industrial equipment?",
                "created_at": datetime.now() - timedelta(hours=1)
            }
        ],
        "description": "Warranty question - should retrieve trading terms"
    },
    {
        "contact": {
            "name": "Emily Thompson",
            "email": "emily.t@retailers.com",
            "company": "Retailers United",
            "tags": [],  # Will be AI-generated from chat history
            "tone_pref": "crisp"
        },
        "thread": [
            {
                "sender": "contact",
                "body": "I want to know about your data retention policy. How long do you keep customer information?",
                "created_at": datetime.now() - timedelta(minutes=30)
            }
        ],
        "description": "Data retention question - should retrieve trading terms"
    },
    {
        "contact": {
            "name": "Michael Brown",
            "email": "michael.b@distributors.com",
            "company": "Distributors Global",
            "tags": [],  # Will be AI-generated from chat history
            "tone_pref": "formal"
        },
        "thread": [
            {
                "sender": "contact",
                "body": "What are the requirements in your supplier code of conduct? We're considering becoming a supplier.",
                "created_at": datetime.now() - timedelta(minutes=15)
            }
        ],
        "description": "Supplier code of conduct question - should retrieve trading terms"
    },
    {
        "contact": {
            "name": "Jennifer Lee",
            "email": "jennifer.lee@consulting.com",
            "company": "Consulting Group",
            "tags": [],  # Will be AI-generated from chat history
            "tone_pref": "warm"
        },
        "thread": [
            {
                "sender": "contact",
                "body": "Can I cancel my order after production has started? What are the cancellation fees?",
                "created_at": datetime.now() - timedelta(minutes=5)
            }
        ],
        "description": "Order cancellation question - should retrieve trading terms"
    },
    {
        "contact": {
            "name": "Thomas Anderson",
            "email": "thomas.a@logistics.com",
            "company": "Logistics Pro",
            "tags": [],  # Will be AI-generated from chat history
            "tone_pref": "crisp"
        },
        "thread": [
            {
                "sender": "contact",
                "body": "What is the maximum liability for claims? I need this for our insurance documentation.",
                "created_at": datetime.now() - timedelta(minutes=2)
            }
        ],
        "description": "Liability question - should retrieve trading terms"
    }
]


@router.post("/seed-rag-test-messages")
async def seed_rag_test_messages_endpoint(_: str = Depends(require_auth)):
    """Seed test mail chains for RAG testing."""
    try:
        pool = await get_pool()
        seeded_count = 0
        
        async with pool.acquire() as conn:
            for chain in TEST_CHAINS:
                try:
                    # Create or get contact
                    # Convert tags list to JSON string
                    tags_json = json.dumps(chain["contact"]["tags"])
                    
                    # Check if contact exists by email
                    existing_contact = await conn.fetchrow(
                        "SELECT id FROM contacts WHERE email = $1",
                        chain["contact"]["email"]
                    )
                    
                    if existing_contact:
                        contact_id = existing_contact["id"]
                        # Update existing contact
                        await conn.execute(
                            """
                            UPDATE contacts 
                            SET name = $1, company = $2, tags = $3, tone_pref = $4
                            WHERE id = $5
                            """,
                            chain["contact"]["name"],
                            chain["contact"]["company"],
                            tags_json,
                            chain["contact"]["tone_pref"],
                            contact_id
                        )
                    else:
                        # Insert new contact
                        contact_id = await conn.fetchval(
                            """
                            INSERT INTO contacts (id, name, email, company, tags, tone_pref, created_at)
                            VALUES ($1, $2, $3, $4, $5, $6, NOW())
                            RETURNING id
                            """,
                            str(uuid.uuid4()),
                            chain["contact"]["name"],
                            chain["contact"]["email"],
                            chain["contact"]["company"],
                            tags_json,
                            chain["contact"]["tone_pref"]
                        )
                    
                    # Create thread
                    thread_id = f"thread_rag_test_{uuid.uuid4().hex[:12]}"
                    
                    # Create messages in thread
                    for msg in chain["thread"]:
                        message_id = str(uuid.uuid4())
                        await conn.execute(
                            """
                            INSERT INTO messages (id, thread_id, contact_id, sender, body, channel, created_at)
                            VALUES ($1, $2, $3, $4, $5, $6, $7)
                            """,
                            message_id,
                            thread_id,
                            contact_id,
                            msg["sender"],
                            msg["body"],
                            "email",
                            msg["created_at"]
                        )
                    
                    # Invalidate cache for this contact and thread
                    from app.services.cache_manager import invalidate_cache
                    from datetime import datetime
                    try:
                        msg_timestamp = datetime.fromisoformat(msg["created_at"].replace('Z', '+00:00')) if isinstance(msg["created_at"], str) else msg.get("created_at")
                        invalidate_cache(
                            reason="new_message",
                            contact_id=contact_id,
                            thread_id=thread_id,
                            message_timestamp=msg_timestamp
                        )
                    except Exception as cache_error:
                        print(f"[Seed] Failed to invalidate cache: {cache_error}")
                    
                    # Trigger tag update in background after creating messages
                    try:
                        from app.services.contact_tags import update_contact_tags
                        import asyncio
                        # Update tags in background (don't wait)
                        asyncio.create_task(update_contact_tags(contact_id, pool))
                    except Exception as e:
                        print(f"[Seed] Failed to trigger tag update for {chain['contact']['name']}: {e}")
                    
                    seeded_count += 1
                    print(f"✅ Seeded: {chain['description']} - {chain['contact']['name']}")
                    
                except Exception as e:
                    print(f"❌ Error seeding chain '{chain['description']}': {e}")
                    continue
        
        return {
            "success": True,
            "message": f"Successfully seeded {seeded_count} test mail chains",
            "chains_seeded": seeded_count
        }
        
    except Exception as e:
        print(f"❌ Error seeding test messages: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Failed to seed test messages: {str(e)}")


# Import tag test chains
from pathlib import Path
import sys
tag_test_script_path = Path(__file__).parent.parent / "scripts" / "seed_tag_test_messages.py"
if tag_test_script_path.exists():
    # Import the TAG_TEST_CHAINS from the script
    import importlib.util
    spec = importlib.util.spec_from_file_location("seed_tag_test_messages", tag_test_script_path)
    tag_test_module = importlib.util.module_from_spec(spec)
    sys.modules["seed_tag_test_messages"] = tag_test_module
    spec.loader.exec_module(tag_test_module)
    TAG_TEST_CHAINS = tag_test_module.TAG_TEST_CHAINS
else:
    TAG_TEST_CHAINS = []


@router.post("/seed-tag-test-messages")
async def seed_tag_test_messages_endpoint(_: str = Depends(require_auth)):
    """Seed test message threads for tag category testing."""
    try:
        if not TAG_TEST_CHAINS:
            raise HTTPException(status_code=500, detail="Tag test chains not found")
        
        pool = await get_pool()
        seeded_count = 0
        
        async with pool.acquire() as conn:
            for chain in TAG_TEST_CHAINS:
                try:
                    # Create or get contact
                    tags_json = json.dumps(chain["contact"]["tags"])
                    
                    # Check if contact exists by email
                    existing_contact = await conn.fetchrow(
                        "SELECT id FROM contacts WHERE email = $1",
                        chain["contact"]["email"]
                    )
                    
                    if existing_contact:
                        contact_id = existing_contact["id"]
                        # Update existing contact
                        await conn.execute(
                            """
                            UPDATE contacts 
                            SET name = $1, company = $2, tags = $3, tone_pref = $4
                            WHERE id = $5
                            """,
                            chain["contact"]["name"],
                            chain["contact"]["company"],
                            tags_json,
                            chain["contact"]["tone_pref"],
                            contact_id
                        )
                    else:
                        # Insert new contact
                        contact_id = await conn.fetchval(
                            """
                            INSERT INTO contacts (id, name, email, company, tags, tone_pref, created_at)
                            VALUES ($1, $2, $3, $4, $5, $6, NOW())
                            RETURNING id
                            """,
                            str(uuid.uuid4()),
                            chain["contact"]["name"],
                            chain["contact"]["email"],
                            chain["contact"]["company"],
                            tags_json,
                            chain["contact"]["tone_pref"]
                        )
                    
                    # Create thread
                    thread_id = f"thread_tag_test_{chain['tag_category']}_{uuid.uuid4().hex[:12]}"
                    
                    # Create messages in thread
                    for msg in chain["thread"]:
                        message_id = str(uuid.uuid4())
                        await conn.execute(
                            """
                            INSERT INTO messages (id, thread_id, contact_id, sender, body, channel, created_at)
                            VALUES ($1, $2, $3, $4, $5, $6, $7)
                            """,
                            message_id,
                            thread_id,
                            contact_id,
                            msg["sender"],
                            msg["body"],
                            "email",
                            msg["created_at"]
                        )
                    
                    # Invalidate cache for this contact and thread
                    from app.services.cache_manager import invalidate_cache
                    try:
                        msg_timestamp = datetime.fromisoformat(msg["created_at"].replace('Z', '+00:00')) if isinstance(msg["created_at"], str) else msg.get("created_at")
                        invalidate_cache(
                            reason="new_message",
                            contact_id=contact_id,
                            thread_id=thread_id,
                            message_timestamp=msg_timestamp
                        )
                    except Exception as cache_error:
                        print(f"[Seed] Failed to invalidate cache: {cache_error}")
                    
                    # Trigger AI tag generation in background after creating messages
                    # LLM will analyze conversation history and generate tags based on criteria
                    try:
                        from app.services.contact_tags import update_contact_tags
                        import asyncio
                        # Update tags in background using LLM (don't wait)
                        asyncio.create_task(update_contact_tags(contact_id, pool))
                        print(f"   → Triggered AI tag generation for {chain['contact']['name']}")
                    except Exception as e:
                        print(f"[Seed] Failed to trigger tag update for {chain['contact']['name']}: {e}")
                    
                    seeded_count += 1
                    print(f"✅ Seeded: {chain['tag_category']} - {chain['description']} - {chain['contact']['name']}")
                    
                except Exception as e:
                    print(f"❌ Error seeding chain '{chain['description']}': {e}")
                    continue
        
        return {
            "success": True,
            "message": f"Successfully seeded {seeded_count} tag test threads",
            "chains_seeded": seeded_count,
            "categories": [chain["tag_category"] for chain in TAG_TEST_CHAINS]
        }
        
    except Exception as e:
        print(f"❌ Error seeding tag test messages: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Failed to seed tag test messages: {str(e)}")

