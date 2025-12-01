"""
MCP Server - Monitoring + Control Plane for Authentication Events
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import logging

from config import settings
from db import init_db
from routes import ingest, events, fraud_assessments, health

# Configure logging
logging.basicConfig(
    level=getattr(logging, settings.LOG_LEVEL.upper()),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)


@asynccontextmanager
async def lifespan(_app: FastAPI):
    """Initialize database on startup"""
    init_db()
    yield


app = FastAPI(
    title="MCP Server",
    description="Monitoring + Control Plane for Authentication Events",
    version="1.0.0",
    lifespan=lifespan
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(ingest.router)
app.include_router(events.router)
app.include_router(fraud_assessments.router)
app.include_router(health.router)


@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "service": "MCP Server",
        "version": "1.0.0",
        "status": "running"
    }
