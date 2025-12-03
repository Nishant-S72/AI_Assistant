#!/usr/bin/env python3
"""Test if backend can access Gemini API"""
import os
import sys
from pathlib import Path

# Add backend_python to path
sys.path.insert(0, str(Path(__file__).parent / "backend_python"))

# Load env like main.py does
from dotenv import load_dotenv
_current_file = Path(__file__).resolve()
project_root = _current_file.parent
env_path = project_root / ".env"

if env_path.exists():
    load_dotenv(dotenv_path=env_path, override=True)
    print(f"✅ Loaded .env from: {env_path}")

api_key = os.getenv("GEMINI_API_KEY")
print(f"API Key: {api_key[:20] + '...' if api_key else 'NOT SET'}")

# Test backend's gemini adapter
try:
    from app.clients.llm.gemini_adapter import generate_with_gemini
    from app.clients.llm.openai_adapter import LLMMessage, LLMOptions
    import asyncio
    
    async def test():
        options = LLMOptions(
            model="gemini-2.5-flash",
            messages=[LLMMessage("user", "Say hello")],
            max_tokens=50,
            temperature=0.3
        )
        result = await generate_with_gemini(options)
        print(f"✅ Backend adapter works: {result.content}")
    
    asyncio.run(test())
except Exception as e:
    print(f"❌ Backend adapter failed: {e}")
    import traceback
    traceback.print_exc()
