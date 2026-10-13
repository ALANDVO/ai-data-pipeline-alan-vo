import time, logging, uuid
from typing import List, Dict, Any, Optional
from dataclasses import dataclass

from backend.app.models.schemas import PipelineRecord
from backend.app.services.orchestrator.pipeline import DAGValidator
from backend.app.core.utils.helpers import generate_id

logger = logging.getLogger(__name__)

class PipelineEngine:
    def __init__(self):
        self.pipelines: Dict[str, PipelineRecord] = {}
        self._seed_demo_pipelines()

    def _seed_demo_pipelines(self):
        demo_nodes = [
            {"id": "extract-orders", "type": "connector", "name": "Extract Orders", "config": {"source": "postgres", "table": "orders"}},
            {"id": "clean-orders", "type": "transform", "name": "Clean Orders", "config": {"nulls": "fill", "dedup": True}},
            {"id": "enrich-orders", "type": "llm", "name": "Enrich Orders", "config": {"task": "categorize"}},
            {"id": "load-warehouse", "type": "connector", "name": "Load to Warehouse", "config": {"target": "bigquery", "dataset": "analytics"}},
        ]
        demo_edges = [
            {"id": "e1", "source": "extract-orders", "target": "clean-orders"},
            {"id": "e2", "source": "clean-orders", "target": "enrich-orders"},
            {"id": "e3", "source": "enrich-orders", "target": "load-warehouse"},
        ]
        now = time.time()
        record = PipelineRecord(
            id="pipe-demo-orders", name="Orders ETL Pipeline",
            description="Extracts orders from Postgres, cleans, enriches with LLM, loads to BigQuery",
            status="active", nodes=demo_nodes, edges=demo_edges,
            created_at=now, updated_at=now, created_by="system",
            last_run_at=now - 3600, last_status="completed",
        )
        self.pipelines[record.id] = record

        demo2_nodes = [
            {"id": "fetch-logs", "type": "connector", "name": "Fetch Logs", "config": {"source": "s3", "path": "logs/"}},
            {"id": "parse-logs", "type": "transform", "name": "Parse Logs", "config": {"format": "json"}},
            {"id": "quality-check", "type": "quality", "name": "Quality Check", "config": {}},
        ]
        demo2_edges = [
            {"id": "e1", "source": "fetch-logs", "target": "parse-logs"},
            {"id": "e2", "source": "parse-logs", "target": "quality-check"},
        ]
        record2 = PipelineRecord(
            id="pipe-demo-logs", name="Log Processing Pipeline",
            description="Fetches logs from S3, parses, and runs quality checks",
            status="active", nodes=demo2_nodes, edges=demo2_edges,
            created_at=now, updated_at=now, created_by="system",
        )
        self.pipelines[record2.id] = record2

    def create_pipeline(self, data: Any, created_by: str = "") -> Dict[str, Any]:
        pid = generate_id("pipe")
        now = time.time()
        record = PipelineRecord(
            id=pid, name=data.name, description=data.description,
            status="active", nodes=[n.dict() for n in data.nodes], edges=[e.dict() for e in data.edges],
            created_at=now, updated_at=now, created_by=created_by,
        )
        self.pipelines[pid] = record
        logger.info("Created pipeline %s: %s", pid, data.name)
        return record.to_dict()

    def get_pipelines(self, status: Optional[str] = None, limit: int = 100) -> List[Dict]:
        pipelines = list(self.pipelines.values())
        if status:
            pipelines = [p for p in pipelines if p.status == status]
        pipelines.sort(key=lambda p: p.created_at, reverse=True)
        return [p.to_dict() for p in pipelines[:limit]]

    def get_pipeline(self, pipeline_id: str) -> Optional[Dict]:
        record = self.pipelines.get(pipeline_id)
        return record.to_dict() if record else None

    def update_pipeline_status(self, pipeline_id: str, status: str):
        record = self.pipelines.get(pipeline_id)
        if record:
            record.status = status
            record.last_run_at = time.time()
            record.last_status = status
            record.updated_at = time.time()

pipeline_engine = PipelineEngine()
