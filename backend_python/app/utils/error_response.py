"""
Consistent error response format for all API endpoints.
"""
from typing import Dict, Any, Optional
from fastapi import HTTPException
from fastapi.responses import JSONResponse


def create_error_response(
    error_type: str,
    message: str,
    status_code: int = 500,
    details: Optional[Dict[str, Any]] = None,
) -> JSONResponse:
    """
    Create a consistent error response format.
    
    Args:
        error_type: Error type (e.g., "validation_error", "not_found", "tier_restriction")
        message: Human-readable error message
        status_code: HTTP status code
        details: Optional additional error details
    
    Returns:
        JSONResponse with consistent error format
    """
    error_data = {
        "success": False,
        "error": {
            "type": error_type,
            "message": message,
        }
    }
    
    if details:
        error_data["error"]["details"] = details
    
    return JSONResponse(
        status_code=status_code,
        content=error_data,
    )


def create_success_response(
    data: Dict[str, Any],
    status_code: int = 200,
) -> JSONResponse:
    """
    Create a consistent success response format.
    
    Args:
        data: Response data
        status_code: HTTP status code
    
    Returns:
        JSONResponse with consistent success format
    """
    return JSONResponse(
        status_code=status_code,
        content={
            "success": True,
            "data": data,
        },
    )

