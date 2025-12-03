#!/usr/bin/env python3
"""
Seed test mail chains for RAG testing.
Creates multiple conversation threads with questions that should trigger RAG retrieval.
"""
import asyncio
import asyncpg
import os
import uuid
from datetime import datetime, timedelta
from pathlib import Path
import sys

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from dotenv import load_dotenv
# Load .env from project root
env_path = Path(__file__).parent.parent.parent / ".env"
load_dotenv(env_path)

# Test mail chains - each designed to test different RAG scenarios
TEST_CHAINS = [
    {
        "contact": {
            "name": "Maria Rodriguez",
            "email": "maria.rodriguez@techcorp.com",
            "company": "TechCorp Solutions",
            "tags": ["lead", "enterprise"],
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
            "tags": ["customer", "trading"],
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
            "tags": ["lead", "shipping"],
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
            "tags": ["customer", "logistics"],
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
            "tags": ["lead", "international"],
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
            "tags": ["customer", "manufacturing"],
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
            "tags": ["lead", "retail"],
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
            "tags": ["customer", "distribution"],
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
            "tags": ["lead", "consulting"],
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
            "tags": ["customer", "logistics"],
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


async def seed_test_messages():
    """Seed test mail chains into the database."""
    # Try to get database URL from environment
    database_url = os.getenv("DATABASE_URL")
    
    # If not set, try to construct from individual components or use default
    if not database_url:
        db_user = os.getenv("DB_USER", "postgres")
        db_password = os.getenv("DB_PASSWORD", "postgres")
        db_host = os.getenv("DB_HOST", "localhost")
        db_port = os.getenv("DB_PORT", "5432")
        db_name = os.getenv("DB_NAME", "aichief")  # Match default from connection.py
        database_url = f"postgresql://{db_user}:{db_password}@{db_host}:{db_port}/{db_name}"
    
    if not database_url:
        print("❌ Database connection not configured. Please set DATABASE_URL or DB_* variables in .env")
        return
    
    try:
        conn = await asyncpg.connect(database_url)
        print("✅ Connected to database")
        
        seeded_count = 0
        
        for chain in TEST_CHAINS:
            try:
                # Create or get contact
                contact_id = await conn.fetchval(
                    """
                    INSERT INTO contacts (id, name, email, company, tags, tone_pref, created_at)
                    VALUES ($1, $2, $3, $4, $5, $6, NOW())
                    ON CONFLICT (email) DO UPDATE SET
                        name = EXCLUDED.name,
                        company = EXCLUDED.company,
                        tags = EXCLUDED.tags,
                        tone_pref = EXCLUDED.tone_pref
                    RETURNING id
                    """,
                    str(uuid.uuid4()),
                    chain["contact"]["name"],
                    chain["contact"]["email"],
                    chain["contact"]["company"],
                    chain["contact"]["tags"],
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
                
                seeded_count += 1
                print(f"✅ Seeded: {chain['description']} - {chain['contact']['name']}")
                
            except Exception as e:
                print(f"❌ Error seeding chain '{chain['description']}': {e}")
                continue
        
        await conn.close()
        print(f"\n✅ Successfully seeded {seeded_count} test mail chains")
        print(f"📧 Total test threads created: {seeded_count}")
        
    except Exception as e:
        print(f"❌ Error connecting to database: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(seed_test_messages())

