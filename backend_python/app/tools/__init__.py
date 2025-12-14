"""Tools module for LLM function calling."""
# Import scheduling registry to auto-register tools
try:
    from . import scheduling_registry
except ImportError:
    # Scheduling tools may not be available in all environments
    pass
