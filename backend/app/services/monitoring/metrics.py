"""Pipeline metrics collection with persistent SQLite storage."""
import json
import time
import logging
from typing import List, Dict, Any, Optional
from collections import defaultdict

from backend.app.core.utils.helpers import generate_id
from backend.app.core.database import get_db
from backend.app.models.database import LogEntryModel, JobModel

logger = logging.getLogger(__name__)

class MetricsCollector:
    """Pipeline metrics collection: duration, throughput, error rates, and log storage."""

    def __init__(self, max_logs: int = 5000):
        self.max_logs = max_logs
        self._seed_demo()

    def _seed_demo(self):
        with get_db() as db:
            count = db.query(LogEntryModel).count()
            if count == 0:
                now = time.time()
                demo_logs = [
                    LogEntryModel(
                        id=generate_id("log"), job_id="job-demo-001", pipeline_id="pipe-demo-orders",
                        level="INFO", message="Pipeline started", context=json.dumps({"source": "engine"}), created_at=now - 3700,
                    ),
                    LogEntryModel(
                        id=generate_id("log"), job_id="job-demo-001", pipeline_id="pipe-demo-orders",
                        level="INFO", message="Extracted 15,200 rows from Postgres", context=json.dumps({"source": "connector:postgres"}), created_at=now - 3690,
                    ),
                    LogEntryModel(
                        id=generate_id("log"), job_id="job-demo-001", pipeline_id="pipe-demo-orders",
                        level="INFO", message="Cleaned 15,200 rows, removed 340 duplicates", context=json.dumps({"source": "transform:clean"}), created_at=now - 3680,
                    ),
                    LogEntryModel(
                        id=generate_id("log"), job_id="job-demo-001", pipeline_id="pipe-demo-orders",
                        level="INFO", message="LLM enrichment completed for 15,200 rows", context=json.dumps({"source": "transform:enrich"}), created_at=now - 3650,
                    ),
                    LogEntryModel(
                        id=generate_id("log"), job_id="job-demo-001", pipeline_id="pipe-demo-orders",
                        level="INFO", message="Loaded 15,200 rows to BigQuery", context=json.dumps({"source": "connector:bigquery"}), created_at=now - 3620,
                    ),
                    LogEntryModel(
                        id=generate_id("log"), job_id="job-demo-001", pipeline_id="pipe-demo-orders",
                        level="INFO", message="Pipeline completed successfully", context=json.dumps({"source": "engine"}), created_at=now - 3610,
                    ),
                    LogEntryModel(
                        id=generate_id("log"), job_id="job-demo-002", pipeline_id="pipe-demo-logs",
                        level="INFO", message="Fetched 45,000 log entries from S3", context=json.dumps({"source": "connector:s3"}), created_at=now - 1800,
                    ),
                    LogEntryModel(
                        id=generate_id("log"), job_id="job-demo-002", pipeline_id="pipe-demo-logs",
                        level="WARNING", message="Found 230 malformed log entries", context=json.dumps({"source": "transform:parse"}), created_at=now - 1790,
                    ),
                    LogEntryModel(
                        id=generate_id("log"), job_id="job-demo-002", pipeline_id="pipe-demo-logs",
                        level="INFO", message="Quality check completed: score 0.87", context=json.dumps({"source": "quality"}), created_at=now - 1780,
                    ),
                ]
                for log in demo_logs:
                    db.add(log)
                db.commit()
                logger.info("Seeded demo logs")

    def log(self, job_id: Optional[str], pipeline_id: Optional[str], level: str, message: str, source: str):
        entry = LogEntryModel(
            id=generate_id("log"),
            job_id=job_id,
            pipeline_id=pipeline_id,
            level=level.upper(),
            message=message,
            context=json.dumps({"source": source}),
            created_at=time.time(),
        )
        with get_db() as db:
            db.add(entry)
            db.commit()
        logger.log(getattr(logging, level.upper(), logging.INFO), "%s: %s [%s]", source, message, job_id or "")

    def record_duration(self, duration_s: float):
        """Record a pipeline run duration (stored via job completion)."""
        pass  # Duration is tracked in JobModel

    def record_rows(self, rows: int):
        """Record rows processed (stored via job tasks)."""
        pass  # Rows are tracked in TaskModel

    def record_error(self, job_id: str, message: str, source: str):
        with get_db() as db:
            job = db.query(JobModel).filter(JobModel.id == job_id).first()
            pipeline_id = job.pipeline_id if job else None
            log = LogEntryModel(
                id=generate_id("log"),
                job_id=job_id,
                pipeline_id=pipeline_id,
                level="ERROR",
                message=message,
                context=json.dumps({"source": source}),
                created_at=time.time(),
            )
            db.add(log)
            db.commit()

    def get_logs(self, job_id: Optional[str] = None, level: Optional[str] = None, limit: int = 200) -> List[Dict]:
        with get_db() as db:
            query = db.query(LogEntryModel)
            if job_id:
                query = query.filter(LogEntryModel.job_id == job_id)
            if level:
                query = query.filter(LogEntryModel.level == level.upper())
            logs = query.order_by(LogEntryModel.created_at.desc()).limit(limit).all()
            return [self._log_to_dict(l) for l in logs]

    def get_summary(self) -> Dict[str, Any]:
        with get_db() as db:
            # Get completed jobs for summary stats
            jobs = db.query(JobModel).filter(JobModel.status == "completed").all()
            durations = [j.duration_ms / 1000.0 for j in jobs if j.duration_ms > 0]
            total_rows = sum(sum(t.rows_processed for t in j.tasks) for j in jobs)
            errors = db.query(LogEntryModel).filter(LogEntryModel.level == "ERROR").count()

            avg_duration = sum(durations) / len(durations) if durations else 0
            error_rate = errors / max(len(durations), 1)
            throughput = total_rows / (sum(durations) or 1)

            return {
                "total_runs": len(durations),
                "avg_duration_s": round(avg_duration, 2),
                "total_rows_processed": total_rows,
                "error_rate": round(error_rate, 4),
                "throughput_rows_per_sec": round(throughput, 2),
            }

    def record_job_completion(self, job_id: str, pipeline_id: str, status: str):
        """Record job completion for metrics tracking."""
        # Already tracked in JobModel; this is a no-op for summary stats
        pass

    @staticmethod
    def _log_to_dict(model: LogEntryModel) -> Dict[str, Any]:
        ctx = {}
        if model.context:
            try:
                ctx = json.loads(model.context)
            except json.JSONDecodeError:
                ctx = {}
        return {
            "id": model.id,
            "job_id": model.job_id,
            "pipeline_id": model.pipeline_id,
            "level": model.level.lower(),
            "message": model.message,
            "timestamp": model.created_at,
            "source": ctx.get("source", ""),
        }


metrics_collector = MetricsCollector()