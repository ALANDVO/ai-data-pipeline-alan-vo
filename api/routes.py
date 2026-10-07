from fastapi import APIRouter, Depends, HTTPException, Query
from typing import List, Optional
from pydantic import BaseModel
import time

from api.auth import get_current_user, User
from api.schemas import (
    Pipeline, PipelineCreate, Job, JobResponse,
    QualityScore, LogEntry, SchemaInference, ConnectorInfo,
    AnomalyResult, SchemaInferRequest
)
from orchestrator.engine import pipeline_engine
from orchestrator.scheduler import job_scheduler
from orchestrator.pipeline import DAGValidator
from monitoring.metrics import metrics_collector
from monitoring.quality import quality_scorer
from monitoring.alerts import alert_evaluator
from transforms.validate import schema_validator
from transforms.enrich import enricher
from connectors.registry import connector_registry
from models.schemas import PipelineRecord, JobRecord

router = APIRouter(prefix="/api", tags=["data-pipeline"])

@router.get("/health")
async def health():
    return {"status": "ok", "service": "ai-data-pipeline", "version": "1.0.0"}

@router.get("/pipelines", response_model=List[Pipeline])
async def get_pipelines(
    status: Optional[str] = Query(None, description="Filter by status: active,paused,failed"),
    limit: int = Query(100, le=500),
    user: User = Depends(get_current_user),
):
    pipelines = pipeline_engine.get_pipelines(status=status, limit=limit)
    return pipelines

@router.post("/pipelines", response_model=Pipeline)
async def create_pipeline(pipeline: PipelineCreate, user: User = Depends(get_current_user)):
    validator = DAGValidator()
    validation = validator.validate(pipeline.nodes, pipeline.edges)
    if not validation["valid"]:
        raise HTTPException(status_code=422, detail={"message": "Invalid DAG", "errors": validation["errors"]})
    result = pipeline_engine.create_pipeline(pipeline, created_by=user.email)
    return result

@router.get("/pipelines/{pipeline_id}")
async def get_pipeline(pipeline_id: str, user: User = Depends(get_current_user)):
    pipeline = pipeline_engine.get_pipeline(pipeline_id)
    if not pipeline:
        raise HTTPException(status_code=404, detail="Pipeline not found")
    return pipeline

@router.post("/pipelines/{pipeline_id}/validate")
async def validate_pipeline(pipeline_id: str, user: User = Depends(get_current_user)):
    pipeline = pipeline_engine.get_pipeline(pipeline_id)
    if not pipeline:
        raise HTTPException(status_code=404, detail="Pipeline not found")
    validator = DAGValidator()
    return validator.validate(pipeline["nodes"], pipeline["edges"])

@router.post("/pipelines/{pipeline_id}/run")
async def run_pipeline(pipeline_id: str, user: User = Depends(get_current_user)):
    pipeline = pipeline_engine.get_pipeline(pipeline_id)
    if not pipeline:
        raise HTTPException(status_code=404, detail="Pipeline not found")
    job = job_scheduler.submit(pipeline_id, triggered_by=user.email)
    return job

@router.get("/jobs", response_model=List[JobResponse])
async def get_jobs(
    status: Optional[str] = Query(None),
    pipeline_id: Optional[str] = Query(None),
    limit: int = Query(100, le=500),
    user: User = Depends(get_current_user),
):
    jobs = job_scheduler.get_jobs(status=status, pipeline_id=pipeline_id, limit=limit)
    return jobs

@router.get("/jobs/{job_id}", response_model=Job)
async def get_job(job_id: str, user: User = Depends(get_current_user)):
    job = job_scheduler.get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return job

@router.post("/jobs/{job_id}/retry")
async def retry_job(job_id: str, user: User = Depends(get_current_user)):
    job = job_scheduler.get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    result = job_scheduler.retry(job_id, triggered_by=user.email)
    return result

@router.get("/quality", response_model=List[QualityScore])
async def get_quality_scores(
    pipeline_id: Optional[str] = Query(None),
    limit: int = Query(50, le=200),
    user: User = Depends(get_current_user),
):
    scores = quality_scorer.get_scores(pipeline_id=pipeline_id, limit=limit)
    return scores

@router.get("/logs", response_model=List[LogEntry])
async def get_logs(
    job_id: Optional[str] = Query(None),
    level: Optional[str] = Query(None),
    limit: int = Query(200, le=1000),
    user: User = Depends(get_current_user),
):
    logs = metrics_collector.get_logs(job_id=job_id, level=level, limit=limit)
    return logs

@router.post("/schema/infer")
async def infer_schema(req: SchemaInferRequest, user: User = Depends(get_current_user)):
    result = await schema_validator.infer_schema(req.sample_rows, req.connector_type)
    return result

@router.get("/connectors", response_model=List[ConnectorInfo])
async def get_connectors(user: User = Depends(get_current_user)):
    return connector_registry.list_connectors()

@router.post("/anomaly/detect")
async def detect_anomaly(req: SchemaInferRequest, user: User = Depends(get_current_user)):
    result = await schema_validator.detect_anomalies(req.sample_rows)
    return result
