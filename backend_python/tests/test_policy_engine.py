"""Tests for policy engine escalation."""
from app.policy.policy_engine import check_policy


def test_escalation_hr_termination():
    """Test that HR/termination keywords trigger escalation."""
    result = check_policy("We need to fire an employee for misconduct")
    assert result["action"] == "ESCALATE"
    assert len(result["reasons"]) > 0
    assert any("termination" in r["reason"].lower() or "hr" in r["reason"].lower() for r in result["reasons"])


def test_escalation_legal():
    """Test that legal keywords trigger escalation."""
    result = check_policy("We're being sued for breach of contract")
    assert result["action"] == "ESCALATE"
    assert len(result["reasons"]) > 0


def test_escalation_sensitive_data():
    """Test that sensitive data keywords trigger escalation."""
    result = check_policy("Customer provided their SSN: 123-45-6789")
    assert result["action"] == "ESCALATE"
    assert result["confidence"] == 1.0  # Highest confidence for PII


def test_no_escalation_general():
    """Test that general messages don't escalate."""
    result = check_policy("How do I write a follow-up email?")
    assert result["action"] == "ALLOW"
    assert len(result["reasons"]) == 0


def test_escalation_harassment():
    """Test that harassment keywords trigger escalation."""
    result = check_policy("There's a complaint about sexual harassment")
    assert result["action"] == "ESCALATE"
    assert any("harassment" in r["reason"].lower() or "hr" in r["reason"].lower() for r in result["reasons"])


def test_escalation_misconduct():
    """Test that misconduct keywords trigger escalation."""
    result = check_policy("Employee misconduct case needs review")
    assert result["action"] == "ESCALATE"

