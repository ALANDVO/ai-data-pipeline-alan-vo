"""Pipeline engine with persistent SQLite storage."""
import time
import logging
from typing import List, Dict, Any, Optional

from backend.app.models.schemas import PipelineRecord
from backend.app.services.orchestrator.pipeline import DAGValidator
from backend.app.core.utils.helpers import generate_id
from backend.app.core.database import get_db
from backend.app.models.database import PipelineModel

logger = logging.getLogger(__name__)


class PipelineEngine:
    def __init__(self):
        self._seed_demo_pipelines()

    def _seed_demo_pipelines(self):
        """Seed demo pipelines if database is empty."""
        with get_db() as db:
            count = db.query(PipelineModel).count()
            if count == 0:
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
                record = PipelineModel(
                    id="pipe-demo-orders", name="Orders ETL Pipeline",
                    description="Extracts orders from Postgres, cleans, enriches with LLM, loads to BigQuery",
                    status="active", created_at=now, updated_at=now, created_by="system",
                    last_run_at=now - 3600, last_status="completed",
                )
                record.set_nodes(demo_nodes)
                record.set_edges(demo_edges)
                db.add(record)

                demo2_nodes = [
                    {"id": "fetch-logs", "type": "connector", "name": "Fetch Logs", "config": {"source": "s3", "path": "logs/"}},
                    {"id": "parse-logs", "type": "transform", "name": "Parse Logs", "config": {"format": "json"}},
                    {"id": "quality-check", "type": "quality", "name": "Quality Check", "config": {}},
                ]
                demo2_edges = [
                    {"id": "e1", "source": "fetch-logs", "target": "parse-logs"},
                    {"id": "e2", "source": "parse-logs", "target": "quality-check"},
                ]
                record2 = PipelineModel(
                    id="pipe-demo-logs", name="Log Processing Pipeline",
                    description="Fetches logs from S3, parses, and runs quality checks",
                    status="active", created_at=now, updated_at=now, created_by="system",
                )
                record2.set_nodes(demo2_nodes)
                record2.set_edges(demo2_edges)
                db.add(record2)
                db.commit()
                logger.info("Seeded demo pipelines")

    def create_pipeline(self, data: Any, created_by: str = "") -> Dict[str, Any]:
        pid = generate_id("pipe")
        now = time.time()
        record = PipelineModel(
            id=pid, name=data.name, description=data.description,
            status="active", created_at=now, updated_at=now, created_by=created_by,
        )
        record.set_nodes([n.dict() for n in data.nodes])
        record.set_edges([e.dict() for e in data.edges])
        with get_db() as db:
            db.add(record)
            db.commit()
            db.refresh(record)
        logger.info("Created pipeline %s: %s", pid, data.name)
        return self._to_dict(record)

    def get_pipelines(self, status: Optional[str] = None, limit: int = 100) -> List[Dict]:
        with get_db() as db:
            query = db.query(PipelineModel)
            if status:
                query = query.filter(PipelineModel.status == status)
            pipelines = query.order_by(PipelineModel.created_at.desc()).limit(limit).all()
            return [self._to_dict(p) for p in pipelines]

    def get_pipeline(self, pipeline_id: str) -> Optional[Dict]:
        with get_db() as db:
            record = db.query(PipelineModel).filter(PipelineModel.id == pipeline_id).first()
            return self._to_dict(record) if record else None

    def update_pipeline_status(self, pipeline_id: str, status: str):
        with get_db() as db:
            record = db.query(PipelineModel).filter(PipelineModel.id == pipeline_id).first()
            if record:
                record.status = status
                record.last_run_at = time.time()
                record.last_status = status
                record.updated_at = time.time()
                db.commit()

    @staticmethod
    def _to_dict(record: PipelineModel) -> Dict[str, Any]:
        return {
            "id": record.id, "name": record.name, "description": record.description,
            "status": record.status, "nodes": record.get_nodes(), "edges": record.get_edges(),
            "created_at": record.created_at, "updated_at": record.updated_at,
            "created_by": record.created_by,
            "last_run_at": record.last_run_at, "last_status": record.last_status,
        }


pipeline_engine = PipelineEngine()