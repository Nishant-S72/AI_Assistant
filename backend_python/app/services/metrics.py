"""Metrics service with Prometheus-style counters."""
from typing import Dict, Any
from datetime import datetime
from app.db.connection import get_pool


class MetricsService:
    """In-memory metrics service."""
    
    def __init__(self):
        self._counters: Dict[str, int] = {
            "total_requests": 0,
            "total_tokens_used": 0,
        }
        self._latencies: list = []
    
    def increment_counter(self, name: str, value: int = 1):
        """Increment a counter."""
        if name not in self._counters:
            self._counters[name] = 0
        self._counters[name] += value
    
    def record_latency(self, latency_ms: int):
        """Record request latency."""
        self._latencies.append(latency_ms)
        # Keep only last 1000 latencies
        if len(self._latencies) > 1000:
            self._latencies = self._latencies[-1000:]
    
    def get_metrics(self) -> Dict[str, Any]:
        """Get current metrics."""
        avg_latency = (
            sum(self._latencies) / len(self._latencies)
            if self._latencies
            else 0
        )
        
        return {
            "total_requests": self._counters.get("total_requests", 0),
            "avg_latency_ms": round(avg_latency, 2),
            "total_tokens_used": self._counters.get("total_tokens_used", 0),
            "timestamp": datetime.now().isoformat(),
        }


# Global metrics service
_metrics_service = MetricsService()


def get_metrics_service() -> MetricsService:
    """Get global metrics service."""
    return _metrics_service

