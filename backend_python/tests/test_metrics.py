"""Tests for metrics service."""
import pytest
from app.services.metrics import MetricsService, get_metrics_service


def test_metrics_service():
    """Test metrics service counters and latency."""
    service = MetricsService()
    
    # Test counters
    service.increment_counter("total_requests", 5)
    service.increment_counter("total_tokens_used", 1000)
    
    # Test latency recording
    service.record_latency(100)
    service.record_latency(200)
    service.record_latency(300)
    
    metrics = service.get_metrics()
    assert metrics["total_requests"] == 5
    assert metrics["total_tokens_used"] == 1000
    assert metrics["avg_latency_ms"] == 200.0  # (100+200+300)/3


def test_metrics_service_global():
    """Test global metrics service instance."""
    service = get_metrics_service()
    assert isinstance(service, MetricsService)

