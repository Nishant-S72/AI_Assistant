#!/usr/bin/env python3
"""
Seed test message threads for tag category testing.
Creates conversation threads that fulfill each of the 6 tag criteria.
Messages are in chronological order with realistic timestamps.
"""
import asyncio
import asyncpg
import os
import uuid
from datetime import datetime, timedelta
from pathlib import Path
import sys
import json

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from dotenv import load_dotenv
# Load .env from project root
env_path = Path(__file__).parent.parent.parent / ".env"
load_dotenv(env_path)

# Test threads for each tag category
# Messages are ordered chronologically (oldest first, newest last)
TAG_TEST_CHAINS = [
    # 1. NEW LEAD - 0-5 messages, recent contact (within 7 days), asking initial questions
    {
        "tag_category": "new-lead",
        "contact": {
            "name": "Alex Thompson",
            "email": "alex.thompson@startup.io",
            "company": "Startup Innovations",
            "tags": [],  # Will be AI-generated
            "tone_pref": "warm"
        },
        "thread": [
            {
                "sender": "contact",
                "body": "Hi there! I came across your company while researching suppliers for our startup. We're looking to expand internationally and I'd love to learn more about what you offer.",
                "created_at": datetime.now() - timedelta(days=2, hours=10)
            },
            {
                "sender": "assistant",
                "body": "Hello Alex! Thanks for reaching out. We'd be happy to help Startup Innovations with your international expansion. We offer comprehensive trading solutions including customs documentation, shipping coordination, and supply chain management. What specific challenges are you facing?",
                "created_at": datetime.now() - timedelta(days=2, hours=9, minutes=15)
            },
            {
                "sender": "contact",
                "body": "That sounds great! We're particularly interested in customs documentation since that's been a pain point for us. Do you handle all the paperwork, or do we need to prepare anything on our end?",
                "created_at": datetime.now() - timedelta(days=2, hours=8, minutes=30)
            },
            {
                "sender": "assistant",
                "body": "We handle the majority of the customs documentation for you. You'll just need to provide basic product information and shipping details. We take care of the rest - forms, declarations, and coordination with customs authorities. Would you like me to send you a detailed overview of our process?",
                "created_at": datetime.now() - timedelta(days=2, hours=7, minutes=45)
            },
            {
                "sender": "contact",
                "body": "Yes please! That would be really helpful. Also, what's your typical turnaround time for processing shipments?",
                "created_at": datetime.now() - timedelta(days=1, hours=16)
            }
        ],
        "description": "New Lead - 5 messages, recent contact, initial questions"
    },
    
    # 2. LONG STANDING - 10+ messages over 30+ days, repeat interactions, loyal relationship
    {
        "tag_category": "long-standing",
        "contact": {
            "name": "Patricia Williams",
            "email": "patricia.w@loyalcustomer.com",
            "company": "Loyal Customer Corp",
            "tags": [],
            "tone_pref": "warm"
        },
        "thread": [
            {
                "sender": "contact",
                "body": "Hi! Hope you're doing well. We've been working together for over a year now and I wanted to check in on our account status.",
                "created_at": datetime.now() - timedelta(days=45, hours=9)
            },
            {
                "sender": "assistant",
                "body": "Hello Patricia! Great to hear from you again. Your account is in excellent standing - all payments are current and your last three orders were delivered on time. How can I assist you today?",
                "created_at": datetime.now() - timedelta(days=45, hours=9, minutes=30)
            },
            {
                "sender": "contact",
                "body": "That's great to hear! We're planning to expand our order volume next quarter as our business is growing. Can we discuss pricing for larger quantities?",
                "created_at": datetime.now() - timedelta(days=40, hours=13)
            },
            {
                "sender": "assistant",
                "body": "Absolutely! I'd be happy to discuss volume pricing with you. Based on your order history, I can offer you a tiered discount structure. Let me prepare a customized quote that reflects your increased volume.",
                "created_at": datetime.now() - timedelta(days=40, hours=13, minutes=45)
            },
            {
                "sender": "contact",
                "body": "Perfect, thank you! Also, I wanted to let you know we're very happy with the quality of your last shipment. Everything arrived in perfect condition, just like always. Keep up the great work!",
                "created_at": datetime.now() - timedelta(days=35, hours=10)
            },
            {
                "sender": "assistant",
                "body": "That's wonderful to hear, Patricia! We really value your continued partnership and feedback. Quality control is something we take very seriously. Is there anything else you need from us?",
                "created_at": datetime.now() - timedelta(days=35, hours=10, minutes=30)
            },
            {
                "sender": "contact",
                "body": "Yes, actually! Can you send me the updated catalog? We're looking to add a few new products to our inventory and I want to see what's available.",
                "created_at": datetime.now() - timedelta(days=30, hours=14)
            },
            {
                "sender": "assistant",
                "body": "Of course! I'll send the latest catalog right away. It includes all our new product lines from this quarter. You should receive it within the hour via email.",
                "created_at": datetime.now() - timedelta(days=30, hours=14, minutes=20)
            },
            {
                "sender": "contact",
                "body": "Perfect, thanks! We've been very satisfied with your service over the past year. Your team is always so helpful and responsive.",
                "created_at": datetime.now() - timedelta(days=25, hours=8)
            },
            {
                "sender": "assistant",
                "body": "We're so glad to hear that, Patricia! Your satisfaction is our top priority, and we truly appreciate your loyalty. Looking forward to continuing our partnership for many more years.",
                "created_at": datetime.now() - timedelta(days=25, hours=8, minutes=45)
            },
            {
                "sender": "contact",
                "body": "Quick question - when will our next scheduled delivery arrive? I need to plan our inventory accordingly.",
                "created_at": datetime.now() - timedelta(days=20, hours=12)
            },
            {
                "sender": "assistant",
                "body": "Your next delivery is scheduled for next Tuesday, the 15th. It should arrive by 2 PM based on the carrier's schedule. I'll send you the tracking information shortly so you can monitor it.",
                "created_at": datetime.now() - timedelta(days=20, hours=12, minutes=30)
            },
            {
                "sender": "contact",
                "body": "Great! Thanks for always being so responsive. You're the best! Talk soon.",
                "created_at": datetime.now() - timedelta(days=15, hours=10)
            }
        ],
        "description": "Long Standing - 13 messages over 45 days, loyal customer relationship"
    },
    
    # 3. URGENT ACTION REQUIRED - Complaints, time-sensitive issues, "asap", "urgent", "emergency"
    {
        "tag_category": "urgent-action-required",
        "contact": {
            "name": "Michael Chen",
            "email": "michael.chen@urgentcorp.com",
            "company": "Urgent Corp",
            "tags": [],
            "tone_pref": "crisp"
        },
        "thread": [
            {
                "sender": "contact",
                "body": "URGENT: Our shipment is delayed and we have a critical deadline tomorrow at 3 PM. This is an emergency situation - our client is waiting and we're at risk of losing a major contract. We need this resolved ASAP!",
                "created_at": datetime.now() - timedelta(hours=3, minutes=15)
            },
            {
                "sender": "assistant",
                "body": "I understand the urgency, Michael. Let me immediately check the status of your shipment and see what we can do to expedite delivery. I'll get back to you within the next 15 minutes with options.",
                "created_at": datetime.now() - timedelta(hours=3, minutes=5)
            },
            {
                "sender": "contact",
                "body": "Thank you, but we really need this TODAY. Our client has been very patient but they can't wait any longer. This is extremely time-sensitive and we're running out of options. Can you escalate this to someone who can make immediate decisions?",
                "created_at": datetime.now() - timedelta(hours=2, minutes=50)
            },
            {
                "sender": "assistant",
                "body": "I've escalated this to our logistics manager and they're working on a solution right now. We're exploring express delivery options and may be able to arrange a same-day courier. I'll have an update for you in the next 10 minutes.",
                "created_at": datetime.now() - timedelta(hours=2, minutes=40)
            },
            {
                "sender": "contact",
                "body": "Please keep me updated. We really can't afford to miss this deadline. I'll be checking my email every few minutes.",
                "created_at": datetime.now() - timedelta(hours=2, minutes=25)
            }
        ],
        "description": "Urgent Action Required - Emergency, time-sensitive, ASAP keywords"
    },
    
    # 4. POTENTIAL INTEREST - Asking about products/services, requesting demos, comparing options, but no purchase yet
    {
        "tag_category": "potential-interest",
        "contact": {
            "name": "Sarah Martinez",
            "email": "sarah.m@exploring.com",
            "company": "Exploring Solutions Inc",
            "tags": [],
            "tone_pref": "warm"
        },
        "thread": [
            {
                "sender": "contact",
                "body": "Hi, I'm researching different suppliers for our upcoming project. Can you tell me more about your product range?",
                "created_at": datetime.now() - timedelta(days=5, hours=13)
            },
            {
                "sender": "assistant",
                "body": "Hello Sarah! We'd be happy to help. We offer a wide range of products including industrial equipment, automation systems, and trading solutions. What specific category are you interested in?",
                "created_at": datetime.now() - timedelta(days=5, hours=13, minutes=30)
            },
            {
                "sender": "contact",
                "body": "I'm looking at industrial equipment. Can you send me a product catalog and pricing information?",
                "created_at": datetime.now() - timedelta(days=4, hours=15)
            },
            {
                "sender": "assistant",
                "body": "Absolutely! I'll send you our comprehensive catalog. Would you also like to schedule a demo to see the products in action?",
                "created_at": datetime.now() - timedelta(days=4, hours=15, minutes=20)
            },
            {
                "sender": "contact",
                "body": "A demo would be great! But first, I'm comparing a few options. Can you tell me how your pricing compares to competitors?",
                "created_at": datetime.now() - timedelta(days=3, hours=10)
            },
            {
                "sender": "assistant",
                "body": "I'd be happy to discuss our competitive advantages. Let me schedule that demo and we can discuss pricing during the call.",
                "created_at": datetime.now() - timedelta(days=3, hours=10, minutes=15)
            },
            {
                "sender": "contact",
                "body": "Sounds good. I'll review the materials you sent and get back to you after I've compared all options.",
                "created_at": datetime.now() - timedelta(days=2, hours=9)
            }
        ],
        "description": "Potential Interest - Asking questions, requesting demos, comparing options, no purchase yet"
    },
    
    # 5. ESCALATION - Dissatisfaction, complaints, refund requests, "speak to manager", "cancel"
    {
        "tag_category": "escalation",
        "contact": {
            "name": "Robert Johnson",
            "email": "robert.j@unhappy.com",
            "company": "Unhappy Customer LLC",
            "tags": [],
            "tone_pref": "formal"
        },
        "thread": [
            {
                "sender": "contact",
                "body": "I'm very dissatisfied with my recent order #4521. The quality was not as promised - several items arrived damaged and the specifications don't match what we agreed upon. I want a full refund immediately.",
                "created_at": datetime.now() - timedelta(days=3, hours=13)
            },
            {
                "sender": "assistant",
                "body": "I'm very sorry to hear about your experience with order #4521, Robert. This is certainly not the level of service we aim to provide. Let me look into this right away and see how we can resolve this for you. I'll need to check with our quality control team first.",
                "created_at": datetime.now() - timedelta(days=3, hours=13, minutes=45)
            },
            {
                "sender": "contact",
                "body": "This is completely unacceptable. I've been a customer for months and this is by far the worst service I've received. I've already sent photos of the damaged items. I want to speak to a manager NOW, not wait for you to 'look into it'.",
                "created_at": datetime.now() - timedelta(days=2, hours=15)
            },
            {
                "sender": "assistant",
                "body": "I completely understand your frustration, Robert. I'm escalating this immediately to our customer relations manager who will contact you directly within the next hour. In the meantime, I'm processing a return authorization for the damaged items.",
                "created_at": datetime.now() - timedelta(days=2, hours=15, minutes=30)
            },
            {
                "sender": "contact",
                "body": "An hour? That's not good enough. If this isn't resolved by tomorrow morning, I'm canceling my account entirely and filing a formal complaint with the Better Business Bureau. This has become a legal matter and I'm documenting everything.",
                "created_at": datetime.now() - timedelta(days=1, hours=10)
            }
        ],
        "description": "Escalation - Complaints, refund requests, speak to manager, cancel threats"
    },
    
    # 6. HIGH PRIORITY - Large orders, premium services, significant revenue, key accounts, executive contacts
    {
        "tag_category": "high-priority",
        "contact": {
            "name": "Elizabeth Anderson",
            "email": "elizabeth.anderson@fortune500.com",
            "company": "Fortune 500 Enterprises",
            "tags": [],
            "tone_pref": "formal"
        },
        "thread": [
            {
                "sender": "contact",
                "body": "Good morning. I'm Elizabeth Anderson, VP of Procurement at Fortune 500 Enterprises. We're currently evaluating suppliers for our premium product line and are interested in placing a large order worth approximately $2.5 million annually. I'd like to discuss how we can establish a strategic partnership.",
                "created_at": datetime.now() - timedelta(days=7, hours=8)
            },
            {
                "sender": "assistant",
                "body": "Good morning Elizabeth! Thank you for reaching out. We'd be honored to work with Fortune 500 Enterprises on this significant opportunity. Given the scale and strategic nature of this partnership, let me connect you immediately with our executive account manager, who specializes in enterprise-level relationships. They'll be able to provide you with a comprehensive proposal tailored to your needs.",
                "created_at": datetime.now() - timedelta(days=7, hours=8, minutes=45)
            },
            {
                "sender": "contact",
                "body": "Excellent. We're looking for a strategic partner, not just a supplier. This is a key account for us, so we need the highest level of service, reliability, and support. What kind of service guarantees can you provide?",
                "created_at": datetime.now() - timedelta(days=6, hours=13)
            },
            {
                "sender": "assistant",
                "body": "Absolutely understood, Elizabeth. For accounts of this magnitude, we provide our premium service tier which includes a dedicated account executive, 99.9% uptime guarantee, priority processing on all orders, and expedited shipping at no additional cost. We'll also assign a technical support specialist to your account. This level of partnership is reserved for our most valued clients.",
                "created_at": datetime.now() - timedelta(days=6, hours=13, minutes=30)
            },
            {
                "sender": "contact",
                "body": "That sounds promising. We're also interested in your premium support package. Can you send me the details for enterprise-level service agreements? I need to review this with our legal team and executive leadership.",
                "created_at": datetime.now() - timedelta(days=5, hours=10)
            },
            {
                "sender": "assistant",
                "body": "Absolutely. I'm sending you our comprehensive enterprise service agreement details right away. This includes 24/7 dedicated support, SLA guarantees, dedicated account management, priority processing, and custom payment terms. I'll also include case studies from similar Fortune 500 partnerships we've established.",
                "created_at": datetime.now() - timedelta(days=5, hours=10, minutes=20)
            },
            {
                "sender": "contact",
                "body": "Excellent. We're prepared to move forward pending review of the agreement. This represents significant revenue for both our companies, and we're looking for a long-term strategic partnership. Let's schedule a call with our executive team - I'll have our CEO and CFO join as well.",
                "created_at": datetime.now() - timedelta(days=4, hours=14)
            },
            {
                "sender": "assistant",
                "body": "That sounds excellent, Elizabeth. I'll coordinate with our executive team to schedule a strategic partnership call. Our CEO and VP of Enterprise Sales will be on the call. I'll send you some available time slots by end of day today.",
                "created_at": datetime.now() - timedelta(days=4, hours=14, minutes=15)
            }
        ],
        "description": "High Priority - Large orders ($2.5M), premium services, executive contacts, key account"
    }
]


async def seed_tag_test_messages():
    """Seed test message threads for tag category testing."""
    # Try to get database URL from environment
    database_url = os.getenv("DATABASE_URL")
    
    # If not set, try to construct from individual components or use default
    if not database_url:
        db_user = os.getenv("DB_USER", "postgres")
        db_password = os.getenv("DB_PASSWORD", "postgres")
        db_host = os.getenv("DB_HOST", "localhost")
        db_port = os.getenv("DB_PORT", "5432")
        db_name = os.getenv("DB_NAME", "aichief")
        database_url = f"postgresql://{db_user}:{db_password}@{db_host}:{db_port}/{db_name}"
    
    if not database_url:
        print("❌ Database connection not configured. Please set DATABASE_URL or DB_* variables in .env")
        return
    
    try:
        conn = await asyncpg.connect(database_url)
        print("✅ Connected to database")
        
        seeded_count = 0
        
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
                
                # Sort messages by timestamp to ensure chronological order (oldest first)
                sorted_messages = sorted(chain["thread"], key=lambda x: x["created_at"])
                
                # Create messages in thread (in chronological order)
                last_msg_timestamp = None
                for msg in sorted_messages:
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
                    last_msg_timestamp = msg["created_at"]
                
                # Invalidate cache for this contact and thread
                try:
                    from app.services.cache_manager import invalidate_cache
                    from datetime import datetime
                    msg_timestamp = datetime.fromisoformat(last_msg_timestamp.replace('Z', '+00:00')) if isinstance(last_msg_timestamp, str) else last_msg_timestamp
                    invalidate_cache(
                        reason="new_message",
                        contact_id=contact_id,
                        thread_id=thread_id,
                        message_timestamp=msg_timestamp
                    )
                except Exception as cache_error:
                    print(f"[Seed] Failed to invalidate cache: {cache_error}")
                
                seeded_count += 1
                print(f"✅ Seeded: {chain['tag_category']} - {chain['description']} - {chain['contact']['name']}")
                
                # Trigger tag generation using LLM (don't wait, run in background)
                try:
                    from app.services.contact_tags import update_contact_tags
                    from app.db.connection import get_pool
                    pool = await get_pool()
                    # Update tags in background - LLM will generate based on criteria
                    asyncio.create_task(update_contact_tags(contact_id, pool))
                    print(f"   → Triggered AI tag generation for {chain['contact']['name']}")
                except Exception as e:
                    print(f"   ⚠️ Failed to trigger tag generation: {e}")
                
            except Exception as e:
                print(f"❌ Error seeding chain '{chain['description']}': {e}")
                import traceback
                traceback.print_exc()
                continue
        
        # Wait a bit for tag generation to complete
        print("\n⏳ Waiting for AI tag generation to complete...")
        await asyncio.sleep(5)
        
        await conn.close()
        print(f"\n✅ Successfully seeded {seeded_count} tag test threads")
        print(f"📧 Total test threads created: {seeded_count}")
        print("\n📋 Tag Categories Expected:")
        for chain in TAG_TEST_CHAINS:
            print(f"   - {chain['tag_category']}: {chain['contact']['name']} ({chain['description']})")
        print("\n💡 Tags are generated by AI based on conversation history and criteria.")
        
    except Exception as e:
        print(f"❌ Error connecting to database: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(seed_tag_test_messages())
