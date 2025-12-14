"""Metrics collector for observability."""
from typing import Dict
from datetime import datetime
import time
from collections import defaultdict
import threading


class MetricsCollector:
    """Thread-safe metrics collector."""
    
    def __init__(self):
        self._lock = threading.Lock()
        self._counters: Dict[str, int] = defaultdict(int)
        self._latencies: list[float] = []
        self._max_latency_samples = 1000
    
    def increment(self, metric_name: str, value: int = 1):
        """Increment a counter."""
        with self._lock:
            self._counters[metric_name] += value
    
    def record_latency(self, latency_ms: float):
        """Record a latency measurement."""
        with self._lock:
            self._latencies.append(latency_ms)
            # Keep only recent samples
            if len(self._latencies) > self._max_latency_samples:
                self._latencies = self._latencies[-self._max_latency_samples:]
    
    def get_metrics(self) -> Dict:
        """Get all metrics."""
        with self._lock:
            total_requests = self._counters.get("total_requests", 0)
            total_tokens = self._counters.get("total_tokens_used", 0)
            
            # Calculate average latency
            if self._latencies:
                avg_latency = sum(self._latencies) / len(self._latencies)
            else:
                avg_latency = 0.0
            
            return {
                "total_requests": total_requests,
                "total_tokens_used": total_tokens,
                "avg_latency_ms": round(avg_latency, 2),
                "timestamp": datetime.now().isoformat(),
            }
    
    def reset(self):
        """Reset all metrics (for testing)."""
        with self._lock:
            self._counters.clear()
            self._latencies.clear()


# Global metrics instance
_metrics = MetricsCollector()


def get_metrics_collector() -> MetricsCollector:
    """Get global metrics collector."""
    return _metrics


