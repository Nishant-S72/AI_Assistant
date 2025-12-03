#!/usr/bin/env python3
"""Comprehensive test script for chat intents with OpenAI."""
import asyncio
import sys
import os
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent.parent / "backend_python"))

from app.policy.intent_classifier import classify_intent_async
from app.routes.chat import handle_general_intent, handle_action_intent, rag_chat
from app.routes.chat import RAGChatRequest
import httpx


API_BASE = "http://localhost:3001"


async def test_intent_classification():
    """Test intent classifier with various messages."""
    print("\n" + "="*60)
    print("TESTING INTENT CLASSIFICATION")
    print("="*60)
    
    test_cases = [
        # General intents
        ("Hi", "general_intent"),
        ("Hello, how are you?", "general_intent"),
        ("What's in my inbox?", "general_intent"),
        ("Tell me about my tasks", "general_intent"),
        ("How many unread messages do I have?", "general_intent"),
        
        # Policy intents
        ("What is our refund policy?", "policy_intent"),
        ("What does the policy say about returns?", "policy_intent"),
        ("Can you check the policy document for eligibility?", "policy_intent"),
        ("According to our policy, what are the rules?", "policy_intent"),
        
        # Action intents
        ("Schedule a meeting tomorrow at 2pm", "action_intent"),
        ("Book a call with john@example.com next Monday", "action_intent"),
        ("Create a calendar event for standup every Monday at 9am", "action_intent"),
        ("Add a meeting on December 15th at 3pm", "action_intent"),
    ]
    
    results = {"passed": 0, "failed": 0, "details": []}
    
    for message, expected_intent in test_cases:
        try:
            result = await classify_intent_async(message)
            if not isinstance(result, dict):
                print(f"\n❌ ERROR | Message: {message[:50]}...")
                print(f"  Error: Result is not a dict: {type(result)}")
                results["failed"] += 1
                continue
            intent = result.get("intent")
            confidence = result.get("confidence", 0.0)
            method = result.get("method", "unknown")
            
            passed = intent == expected_intent
            status = "✅ PASS" if passed else "❌ FAIL"
            
            if passed:
                results["passed"] += 1
            else:
                results["failed"] += 1
            
            print(f"\n{status} | Intent: {intent} (expected: {expected_intent})")
            print(f"  Message: {message[:50]}...")
            print(f"  Confidence: {confidence:.2f} | Method: {method}")
            
            results["details"].append({
                "message": message,
                "expected": expected_intent,
                "got": intent,
                "confidence": confidence,
                "passed": passed
            })
        except Exception as e:
            print(f"\n❌ ERROR | Message: {message[:50]}...")
            print(f"  Error: {e}")
            results["failed"] += 1
    
    print(f"\n{'='*60}")
    print(f"Classification Results: {results['passed']}/{len(test_cases)} passed")
    print(f"{'='*60}\n")
    
    return results


async def test_general_intent():
    """Test general intent handler."""
    print("\n" + "="*60)
    print("TESTING GENERAL INTENT")
    print("="*60)
    
    test_messages = [
        "Hi",
        "Hello!",
        "What's in my inbox?",
        "How many tasks do I have?",
        "Tell me about my unread messages",
    ]
    
    results = []
    for message in test_messages:
        try:
            print(f"\nTesting: {message}")
            response = await handle_general_intent(message, None, "warm")
            
            text = response.get("text", "")
            intent = response.get("intent", "unknown")
            
            print(f"  ✅ Response received")
            print(f"  Intent: {intent}")
            print(f"  Response length: {len(text)} chars")
            print(f"  Preview: {text[:100]}...")
            
            results.append({
                "message": message,
                "success": True,
                "intent": intent,
                "response_length": len(text)
            })
        except Exception as e:
            print(f"  ❌ Error: {e}")
            results.append({
                "message": message,
                "success": False,
                "error": str(e)
            })
    
    passed = sum(1 for r in results if r.get("success"))
    print(f"\n{'='*60}")
    print(f"General Intent Results: {passed}/{len(test_messages)} passed")
    print(f"{'='*60}\n")
    
    return results


async def test_policy_intent():
    """Test policy intent handler."""
    print("\n" + "="*60)
    print("TESTING POLICY INTENT")
    print("="*60)
    
    test_messages = [
        "What is our refund policy?",
        "What does the policy say about returns?",
        "Can you check the policy document?",
    ]
    
    results = []
    for message in test_messages:
        try:
            print(f"\nTesting: {message}")
            request = RAGChatRequest(
                userMessage=message,
                tone="warm",
                rag=True
            )
            response = await rag_chat(request)
            
            text = response.get("text", "")
            intent = response.get("intent", "unknown")
            citations = response.get("citations", [])
            
            print(f"  ✅ Response received")
            print(f"  Intent: {intent}")
            print(f"  Citations: {len(citations)}")
            print(f"  Response length: {len(text)} chars")
            print(f"  Preview: {text[:100]}...")
            
            results.append({
                "message": message,
                "success": True,
                "intent": intent,
                "citations_count": len(citations),
                "response_length": len(text)
            })
        except Exception as e:
            print(f"  ❌ Error: {e}")
            import traceback
            traceback.print_exc()
            results.append({
                "message": message,
                "success": False,
                "error": str(e)
            })
    
    passed = sum(1 for r in results if r.get("success"))
    print(f"\n{'='*60}")
    print(f"Policy Intent Results: {passed}/{len(test_messages)} passed")
    print(f"{'='*60}\n")
    
    return results


async def test_action_intent():
    """Test action intent handler."""
    print("\n" + "="*60)
    print("TESTING ACTION INTENT")
    print("="*60)
    
    test_messages = [
        "Schedule a meeting tomorrow at 2pm",
        "Book a call next Monday at 10am",
        "Create a calendar event for standup every Monday at 9am",
    ]
    
    results = []
    for message in test_messages:
        try:
            print(f"\nTesting: {message}")
            # First classify intent
            intent_result = await classify_intent_async(message)
            print(f"  Classified as: {intent_result.get('intent')} (confidence: {intent_result.get('confidence', 0):.2f})")
            
            if intent_result.get("intent") == "action_intent":
                response = await handle_action_intent(message, None, "warm", intent_result)
                
                text = response.get("text", "")
                intent = response.get("intent", "unknown")
                action_result = response.get("action_result", {})
                
                print(f"  ✅ Response received")
                print(f"  Intent: {intent}")
                print(f"  Action success: {action_result.get('success', False)}")
                print(f"  Response: {text[:150]}...")
                
                results.append({
                    "message": message,
                    "success": True,
                    "intent": intent,
                    "action_success": action_result.get("success", False),
                    "response_length": len(text)
                })
            else:
                print(f"  ⚠️  Intent misclassified as: {intent_result.get('intent')}")
                results.append({
                    "message": message,
                    "success": False,
                    "error": f"Intent misclassified: {intent_result.get('intent')}"
                })
        except Exception as e:
            print(f"  ❌ Error: {e}")
            import traceback
            traceback.print_exc()
            results.append({
                "message": message,
                "success": False,
                "error": str(e)
            })
    
    passed = sum(1 for r in results if r.get("success") and r.get("action_success", False))
    print(f"\n{'='*60}")
    print(f"Action Intent Results: {passed}/{len(test_messages)} passed")
    print(f"{'='*60}\n")
    
    return results


async def test_end_to_end_chat():
    """Test end-to-end chat API."""
    print("\n" + "="*60)
    print("TESTING END-TO-END CHAT API")
    print("="*60)
    
    test_cases = [
        {"userMessage": "Hi", "expected_intent": "general_intent"},
        {"userMessage": "What is our refund policy?", "expected_intent": "policy_intent"},
        {"userMessage": "Schedule a meeting tomorrow at 2pm", "expected_intent": "action_intent"},
    ]
    
    results = []
    async with httpx.AsyncClient(timeout=30.0) as client:
        for test in test_cases:
            try:
                message = test["userMessage"]
                expected = test["expected_intent"]
                
                print(f"\nTesting: {message}")
                response = await client.post(
                    f"{API_BASE}/api/chat",
                    json={"userMessage": message, "tone": "warm"},
                    timeout=30.0
                )
                
                if response.status_code == 200:
                    data = response.json()
                    intent = data.get("intent", "unknown")
                    text = data.get("text", "") or data.get("answer", "")
                    
                    passed = intent == expected
                    status = "✅ PASS" if passed else "⚠️  INTENT MISMATCH"
                    
                    print(f"  {status}")
                    print(f"  Intent: {intent} (expected: {expected})")
                    print(f"  Response: {text[:100]}...")
                    
                    results.append({
                        "message": message,
                        "success": True,
                        "intent": intent,
                        "expected": expected,
                        "passed": passed
                    })
                else:
                    print(f"  ❌ HTTP {response.status_code}: {response.text[:200]}")
                    results.append({
                        "message": message,
                        "success": False,
                        "error": f"HTTP {response.status_code}"
                    })
            except Exception as e:
                print(f"  ❌ Error: {e}")
                results.append({
                    "message": test["userMessage"],
                    "success": False,
                    "error": str(e)
                })
    
    passed = sum(1 for r in results if r.get("success") and r.get("passed", False))
    print(f"\n{'='*60}")
    print(f"End-to-End Results: {passed}/{len(test_cases)} passed")
    print(f"{'='*60}\n")
    
    return results


async def main():
    """Run all tests."""
    print("\n" + "="*60)
    print("CHAT INTENT TESTING SUITE - OpenAI")
    print("="*60)
    
    # Check if backend is running
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.get(f"{API_BASE}/api/health")
            if response.status_code == 200:
                health = response.json()
                print(f"✅ Backend is running")
                print(f"   LLM: {health.get('llm', 'unknown')}")
                print(f"   Database: {health.get('database', 'unknown')}")
            else:
                print(f"⚠️  Backend health check returned {response.status_code}")
    except Exception as e:
        print(f"❌ Cannot connect to backend at {API_BASE}")
        print(f"   Error: {e}")
        print(f"   Please ensure backend is running on port 3001")
        return
    
    # Run tests
    classification_results = await test_intent_classification()
    general_results = await test_general_intent()
    policy_results = await test_policy_intent()
    action_results = await test_action_intent()
    e2e_results = await test_end_to_end_chat()
    
    # Summary
    print("\n" + "="*60)
    print("FINAL SUMMARY")
    print("="*60)
    print(f"Intent Classification: {classification_results['passed']}/{len(classification_results['details'])} passed")
    print(f"General Intent: {sum(1 for r in general_results if r.get('success'))}/{len(general_results)} passed")
    print(f"Policy Intent: {sum(1 for r in policy_results if r.get('success'))}/{len(policy_results)} passed")
    print(f"Action Intent: {sum(1 for r in action_results if r.get('success') and r.get('action_success'))}/{len(action_results)} passed")
    print(f"End-to-End: {sum(1 for r in e2e_results if r.get('success') and r.get('passed'))}/{len(e2e_results)} passed")
    print("="*60 + "\n")


if __name__ == "__main__":
    asyncio.run(main())

