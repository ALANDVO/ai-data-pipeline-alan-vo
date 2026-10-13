from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from enum import Enum

class PipelineStatus(str, Enum):
    active = "active"
    paused = "paused"
    failed = "failed"
    running = "running"

class NodeDef(BaseModel):
    id: str
    type: str = "transform"
    name: str = ""
    config: Dict[str, Any] = Field(default_factory=dict)
    position: Dict[str, float] = Field(default_factory=dict)

class EdgeDef(BaseModel):
    id: str
    source: str
    target: str

class PipelineCreate(BaseModel):
    name: str
    description: str = ""
    nodes: List[NodeDef]
    edges: List[EdgeDef]

class Pipeline(BaseModel):
    id: str
    name: str
    description: str = ""
    status: str = "active"
    nodes: List[NodeDef] = Field(default_factory=list)
    edges: List[EdgeDef] = Field(default_factory=list)
    created_at: float = 0
    updated_at: float = 0
    created_by: str = ""
    last_run_at: Optional[float] = None
    last_status: Optional[str] = None

class TaskResult(BaseModel):
    task_id: str
    status: str = "pending"
    rows_processed: int = 0
    duration_ms: float = 0
    error: Optional[str] = None
    retries: int = 0
    output: Dict[str, Any] = Field(default_factory=dict)

class Job(BaseModel):
    id: str
    pipeline_id: str
    status: str = "queued"
    triggered_by: str = ""
    started_at: Optional[float] = None
    completed_at: Optional[float] = None
    duration_ms: float = 0
    tasks: List[TaskResult] = Field(default_factory=list)
    error: Optional[str] = None

class JobResponse(BaseModel):
    id: str
    pipeline_id: str
    status: str
    triggered_by: str = ""
    started_at: Optional[float] = None
    completed_at: Optional[float] = None
    duration_ms: float = 0
    tasks: List[TaskResult] = Field(default_factory=list)
    error: Optional[str] = None

class QualityScore(BaseModel):
    pipeline_id: str
    dataset: str
    completeness: float = 0
    accuracy: float = 0
    consistency: float = 0
    timeliness: float = 0
    overall: float = 0
    issues: List[str] = Field(default_factory=list)
    scored_at: float = 0

class LogEntry(BaseModel):
    id: str
    job_id: Optional[str] = None
    pipeline_id: Optional[str] = None
    level: str = "info"
    message: str = ""
    timestamp: float = 0
    source: str = ""

class SchemaField(BaseModel):
    name: str
    type: str
    nullable: bool = True
    description: str = ""
    sample_values: List[str] = Field(default_factory=list)

class SchemaInference(BaseModel):
    fields: List[SchemaField]
    primary_key: Optional[str] = None
    inferred_at: float = 0
    confidence: float = 0

class SchemaInferRequest(BaseModel):
    sample_rows: List[Dict[str, Any]]
    connector_type: str = "postgres"

class ConnectorInfo(BaseModel):
    type: str
    name: str
    status: str = "configured"
    config_summary: Dict[str, Any] = Field(default_factory=dict)

class AnomalyResult(BaseModel):
    detected: bool
    anomalies: List[Dict[str, Any]] = Field(default_factory=list)
    summary: str = ""
    confidence: float = 0
