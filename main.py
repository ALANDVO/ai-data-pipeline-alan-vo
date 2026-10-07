#!/usr/bin/env python3
"""AI Data Pipeline Orchestrator — main entry point."""
import sys, os, logging
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from config import settings
from utils.logging import setup_logging
from api.routes import router as api_router

logging.basicConfig(level=getattr(logging, settings.log_level, logging.INFO))
logger = logging.getLogger(__name__)

app = FastAPI(
    title="AI Data Pipeline Orchestrator",
    version="1.0.0",
    description="Enterprise AI-powered data pipeline orchestrator with visual DAG builder, LLM schema inference, data quality scoring, and multi-cloud connectors.",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router)

if os.path.exists("frontend/dist"):
    app.mount("/", StaticFiles(directory="frontend/dist", html=True), name="frontend")

@app.on_event("startup")
async def startup():
    logger.info("AI Data Pipeline Orchestrator starting on %s:%s", settings.host, settings.port)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host=settings.host, port=settings.port)
