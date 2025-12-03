#!/usr/bin/env python3
"""Call the seed function directly from the backend's seed endpoint."""
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

# Import the seed function directly
from app.routes.policydoc import seed_policy_documents

async def main():
    """Call the seed function."""
    try:
        result = await seed_policy_documents()
        print("✅ Seed result:", result)
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(main())

