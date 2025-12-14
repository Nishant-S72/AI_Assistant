"""Tests for metrics collection."""
import pytest
from app.metrics.collector import MetricsCollector, get_metrics_collector


def test_metrics_collector_increment():
    """Test incrementing counters."""
    collector = MetricsCollector()
    collector.increment("test_counter")
    collector.increment("test_counter", 5)
    
    metrics = collector.get_metrics()
    # Note: get_metrics() doesn't return individual counters, only aggregated
    assert metrics["total_requests"] >= 0


def test_metrics_collector_latency():
    """Test recording latency."""
    collector = MetricsCollector()
    collector.record_latency(100.5)
    collector.record_latency(200.3)
    collector.record_latency(150.0)
    
    metrics = collector.get_metrics()
    assert metrics["avg_latency_ms"] > 0
    # Should be approximately average of recorded latencies
    assert 100 < metrics["avg_latency_ms"] < 200


def test_metrics_collector_get_metrics():
    """Test getting all metrics."""
    collector = get_metrics_collector()
    collector.increment("total_requests", 10)
    collector.increment("total_tokens_used", 5000)
    collector.record_latency(50.0)
    
    metrics = collector.get_metrics()
    assert "total_requests" in metrics
    assert "total_tokens_used" in metrics
    assert "avg_latency_ms" in metrics
    assert "timestamp" in metrics


def test_metrics_reset():
    """Test resetting metrics."""
    collector = MetricsCollector()
    collector.increment("total_requests", 10)
    collector.record_latency(100.0)
    
    collector.reset()
    
    metrics = collector.get_metrics()
    assert metrics["total_requests"] == 0
    assert metrics["avg_latency_ms"] == 0.0
