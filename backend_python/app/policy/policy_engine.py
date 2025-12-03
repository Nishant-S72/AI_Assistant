"""Policy engine for message escalation."""
import json
import os
from pathlib import Path
from typing import Dict, List, Any

# Default policy rules
DEFAULT_RULES = [
    {
        "keywords": ["refund", "refunds", "money back"],
        "action": "ESCALATE",
        "reason": "Contains refund-related keywords",
        "confidence": 0.9,
    },
    {
        "keywords": ["lawsuit", "sue", "suing", "legal action", "attorney", "lawyer", "litigation", "court", "legal complaint"],
        "action": "ESCALATE",
        "reason": "Contains legal action keywords",
        "confidence": 0.95,
    },
    {
        "keywords": ["legal", "litigation", "court", "breach of contract"],
        "action": "ESCALATE",
        "reason": "Contains legal terminology",
        "confidence": 0.85,
    },
    {
        "keywords": ["chargeback", "dispute", "fraud"],
        "action": "ESCALATE",
        "reason": "Contains payment dispute keywords",
        "confidence": 0.9,
    },
    {
        "keywords": ["ssn", "social security", "credit card number", "cvv", "passport", "visa", "bank account", "medical record", "diagnosis", "criminal record"],
        "action": "ESCALATE",
        "reason": "Contains sensitive personal information",
        "confidence": 1.0,
    },
    {
        "keywords": ["harassment", "sexual harassment", "discrimination", "grievance", "complaint against employee"],
        "action": "ESCALATE",
        "reason": "Contains HR/sensitive workplace keywords",
        "confidence": 0.95,
    },
    {
        "keywords": ["fire", "terminate", "termination", "fired", "dismissal", "dismiss", "layoff", "lay off", "misconduct", "employee misconduct"],
        "action": "ESCALATE",
        "reason": "Contains HR/termination keywords",
        "confidence": 0.95,
    },
    {
        "keywords": ["passport", "visa", "immigration", "citizenship"],
        "action": "ESCALATE",
        "reason": "Contains immigration/legal document keywords",
        "confidence": 0.9,
    },
    {
        "keywords": ["criminal", "felony", "arrest", "conviction"],
        "action": "ESCALATE",
        "reason": "Contains criminal/legal keywords",
        "confidence": 0.95,
    },
    {
        "keywords": ["medical", "diagnosis", "health condition", "disability"],
        "action": "ESCALATE",
        "reason": "Contains medical/health information",
        "confidence": 0.9,
    },
    {
        "keywords": ["contract drafting", "legal opinion", "legal advice"],
        "action": "ESCALATE",
        "reason": "Request for legal services",
        "confidence": 0.95,
    },
]

_rules: List[Dict[str, Any]] = []


def _load_rules() -> None:
    """Load policy rules from file or use defaults."""
    global _rules
    try:
        # Try multiple paths
        possible_paths = [
            Path(__file__).parent.parent.parent / "policy.json",
            Path(__file__).parent.parent.parent.parent / "backend" / "policy.json",
        ]

        policy_path = None
        for path in possible_paths:
            if path.exists():
                policy_path = path
                break

        if policy_path:
            with open(policy_path, "r", encoding="utf-8") as f:
                config = json.load(f)
                _rules = config.get("rules", [])
        else:
            _rules = DEFAULT_RULES
    except Exception as error:
        print(f"[Policy] Error loading rules: {error}")
        # Use default rules instead of recursive call to prevent infinite recursion
        _rules = DEFAULT_RULES


def check_policy(message_body: str) -> Dict[str, Any]:
    """Check message against policy rules.
    
    NOTE: This is an onboard RAG bot with NO human backup.
    Policy questions (asking ABOUT policies) should ALWAYS be allowed and answered via RAG.
    This function is kept for compatibility but should not escalate policy questions.
    """
    if not _rules:
        _load_rules()

    lower_body = message_body.lower()
    
    # Check if this is a policy question (asking ABOUT policy, not requesting action)
    # Policy questions should be allowed through to policy_intent handler
    # IMPORTANT: This is an onboard RAG bot - policy questions should NOT be escalated
    policy_question_patterns = [
        r'what (is|are) (our|the) (refund|return|policy|policies)',
        r'what does (the|our) (policy|policies) (say|state|say about)',
        r'according to (the|our) (policy|policies)',
        r'check (the|our) (policy|policies)',
        r'(policy|policies) (document|documents)',
        r'what (is|are) (the|our) (rule|rules|guideline|guidelines)',
        r'can (you|we) (check|see|look at) (the|our) (policy|policies)',
        r'tell me (about|more about) (the|our|a) (refund|return|policy|policies|rule|rules)',
        r'explain (the|our|a) (refund|return|policy|policies|rule|rules)',
        r'describe (the|our|a) (refund|return|policy|policies|rule|rules)',
        r'information (about|on) (the|our|a) (refund|return|policy|policies)',
        r'(refund|return|policy|policies|rule|rules) (information|details|explanation)',
        r'how (does|do) (the|our) (refund|return|policy|policies) (work|apply)',
    ]
    
    import re
    is_policy_question = any(re.search(pattern, lower_body, re.IGNORECASE) for pattern in policy_question_patterns)
    
    # If it's a policy question, allow it through (don't escalate)
    if is_policy_question:
        return {
            "action": "ALLOW",
            "reasons": [],
            "confidence": 0.0,
        }

    reasons = []
    max_confidence = 0.0

    for rule in _rules:
        keywords = rule.get("keywords", [])
        for keyword in keywords:
            if keyword.lower() in lower_body:
                reasons.append({
                    "keyword": keyword,
                    "action": rule.get("action", "ESCALATE"),
                    "reason": rule.get("reason", "Contains sensitive keyword"),
                    "confidence": rule.get("confidence", 0.8),
                })
                max_confidence = max(max_confidence, rule.get("confidence", 0.8))
                break  # Only count each rule once

    if reasons:
        return {
            "action": "ESCALATE",
            "reasons": reasons,
            "confidence": max_confidence,
        }

    return {
        "action": "ALLOW",
        "reasons": [],
        "confidence": 0.0,
    }

