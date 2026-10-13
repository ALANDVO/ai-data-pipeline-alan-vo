from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional
from datetime import datetime

@dataclass
class PipelineRecord:
    id: str
    name: str
    description: str = ""
    status: str = "active"
    nodes: List[Dict[str, Any]] = field(default_factory=list)
    edges: List[Dict[str, Any]] = field(default_factory=list)
    created_at: float = 0
    updated_at: float = 0
    created_by: str = ""
    last_run_at: Optional[float] = None
    last_status: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id, "name": self.name, "description": self.description,
            "status": self.status, "nodes": self.nodes, "edges": self.edges,
            "created_at": self.created_at, "updated_at": self.updated_at,
            "created_by": self.created_by,
            "last_run_at": self.last_run_at, "last_status": self.last_status,
        }

@dataclass
class TaskRecord:
    task_id: str
    status: str = "pending"
    rows_processed: int = 0
    duration_ms: float = 0
    error: Optional[str] = None
    retries: int = 0
    output: Dict[str, Any] = field(default_factory=dict)

@dataclass
class JobRecord:
    id: str
    pipeline_id: str
    status: str = "queued"
    triggered_by: str = ""
    started_at: Optional[float] = None
    completed_at: Optional[float] = None
    duration_ms: float = 0
    tasks: List[TaskRecord] = field(default_factory=list)
    error: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id, "pipeline_id": self.pipeline_id,
            "status": self.status, "triggered_by": self.triggered_by,
            "started_at": self.started_at, "completed_at": self.completed_at,
            "duration_ms": self.duration_ms,
            "tasks": [
                {"task_id": t.task_id, "status": t.status, "rows_processed": t.rows_processed,
                 "duration_ms": t.duration_ms, "error": t.error, "retries": t.retries,
                 "output": t.output}
                for t in self.tasks
            ],
            "error": self.error,
        }
