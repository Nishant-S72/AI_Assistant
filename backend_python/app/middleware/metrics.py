"""Metrics middleware to track requests and latency."""
from fastapi import Request
from time import time
from app.metrics.collector import get_metrics_collector


async def metrics_middleware(request: Request, call_next):
    """Middleware to track request metrics."""
    metrics = get_metrics_collector()
    
    # Skip metrics for health checks
    if request.url.path.startswith("/api/health"):
        return await call_next(request)
    
    start_time = time()
    
    # Process request
    response = await call_next(request)
    
    # Calculate latency
    latency_ms = (time() - start_time) * 1000
    
    # Record metrics
    metrics.increment("total_requests")
    metrics.record_latency(latency_ms)
    
    # Extract token usage from response headers
    tokens_used = response.headers.get("X-Tokens-Used")
    if tokens_used:
        try:
            metrics.increment("total_tokens_used", int(tokens_used))
        except ValueError:
            pass
    
    return response


