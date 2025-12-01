"""
Health check endpoints for MCP Server
"""
from fastapi import APIRouter, status
from datetime import datetime
from typing import Dict, Any

from db import check_db_connection
from config import settings

router = APIRouter(tags=["health"])


@router.get("/health", status_code=status.HTTP_200_OK)
async def health_check() -> Dict[str, Any]:
    """
    Basic health check endpoint.

    Returns:
        dict: Health status and timestamp
    """
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat()
    }


@router.get("/ready", status_code=status.HTTP_200_OK)
async def readiness_check() -> Dict[str, Any]:
    """
    Readiness check endpoint with database and BAML agent status.

    Returns:
        dict: Readiness status with component health

    Raises:
        HTTPException: 503 if service is not ready
    """
    # Check database connectivity
    db_connected = check_db_connection()

    # Check BAML agent availability
    baml_status = "available" if settings.BAML_ENABLED else "disabled"

    # Determine overall readiness
    is_ready = db_connected

    response = {
        "status": "ready" if is_ready else "not_ready",
        "database": "connected" if db_connected else "disconnected",
        "baml_agent": baml_status,
        "timestamp": datetime.utcnow().isoformat()
    }

    # Return 503 if not ready
    if not is_ready:
        from fastapi import HTTPException
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=response
        )

    return response
