import time, logging, uuid
from typing import List, Dict, Any, Optional
from collections import defaultdict

from backend.app.core.utils.helpers import generate_id

logger = logging.getLogger(__name__)

class MetricsCollector:
    '''Pipeline metrics collection: duration, throughput, error rates, and log storage.'''

    def __init__(self, max_logs: int = 5000):
        self.max_logs = max_logs
        self.logs: List[Dict[str, Any]] = []
        self._durations: List[float] = []
        self._rows_processed: List[int] = []
        self._errors: List[Dict] = []
        self._seed_demo()

    def _seed_demo(self):
        now = time.time()
        demo_logs = [
            {"id": generate_id("log"), "job_id": "job-demo-001", "pipeline_id": "pipe-demo-orders", "level": "info", "message": "Pipeline started", "timestamp": now - 3700, "source": "engine"},
            {"id": generate_id("log"), "job_id": "job-demo-001", "pipeline_id": "pipe-demo-orders", "level": "info", "message": "Extracted 15,200 rows from Postgres", "timestamp": now - 3690, "source": "connector:postgres"},
            {"id": generate_id("log"), "job_id": "job-demo-001", "pipeline_id": "pipe-demo-orders", "level": "info", "message": "Cleaned 15,200 rows, removed 340 duplicates", "timestamp": now - 3680, "source": "transform:clean"},
            {"id": generate_id("log"), "job_id": "job-demo-001", "pipeline_id": "pipe-demo-orders", "level": "info", "message": "LLM enrichment completed for 15,200 rows", "timestamp": now - 3650, "source": "transform:enrich"},
            {"id": generate_id("log"), "job_id": "job-demo-001", "pipeline_id": "pipe-demo-orders", "level": "info", "message": "Loaded 15,200 rows to BigQuery", "timestamp": now - 3620, "source": "connector:bigquery"},
            {"id": generate_id("log"), "job_id": "job-demo-001", "pipeline_id": "pipe-demo-orders", "level": "info", "message": "Pipeline completed successfully", "timestamp": now - 3610, "source": "engine"},
            {"id": generate_id("log"), "job_id": "job-demo-002", "pipeline_id": "pipe-demo-logs", "level": "info", "message": "Fetched 45,000 log entries from S3", "timestamp": now - 1800, "source": "connector:s3"},
            {"id": generate_id("log"), "job_id": "job-demo-002", "pipeline_id": "pipe-demo-logs", "level": "warning", "message": "Found 230 malformed log entries", "timestamp": now - 1790, "source": "transform:parse"},
            {"id": generate_id("log"), "job_id": "job-demo-002", "pipeline_id": "pipe-demo-logs", "level": "info", "message": "Quality check completed: score 0.87", "timestamp": now - 1780, "source": "quality"},
        ]
        self.logs = demo_logs
        self._durations = [3.2, 4.1, 2.8, 5.5, 3.9, 4.4, 6.1, 3.5, 4.7]
        self._rows_processed = [15200, 45000, 12800, 8900, 23400, 15200, 31000, 15200, 19800]
        self._errors = [
            {"timestamp": now - 7200, "job_id": "job-demo-000", "message": "Connection timeout to BigQuery", "source": "connector:bigquery"},
        ]

    def log(self, job_id: Optional[str], pipeline_id: Optional[str], level: str, message: str, source: str):
        entry = {
            "id": generate_id("log"),
            "job_id": job_id,
            "pipeline_id": pipeline_id,
            "level": level,
            "message": message,
            "timestamp": time.time(),
            "source": source,
        }
        self.logs.append(entry)
        if len(self.logs) > self.max_logs:
            self.logs = self.logs[-self.max_logs:]
        logger.log(getattr(logging, level.upper(), logging.INFO), "%s: %s [%s]", source, message, job_id or "")

    def record_duration(self, duration_s: float):
        self._durations.append(duration_s)

    def record_rows(self, rows: int):
        self._rows_processed.append(rows)

    def record_error(self, job_id: str, message: str, source: str):
        self._errors.append({"timestamp": time.time(), "job_id": job_id, "message": message, "source": source})

    def get_logs(self, job_id: Optional[str] = None, level: Optional[str] = None, limit: int = 200) -> List[Dict]:
        logs = list(self.logs)
        if job_id:
            logs = [l for l in logs if l.get("job_id") == job_id]
        if level:
            logs = [l for l in logs if l["level"] == level]
        logs.sort(key=lambda l: l["timestamp"], reverse=True)
        return logs[:limit]

    def get_summary(self) -> Dict[str, Any]:
        avg_duration = sum(self._durations) / len(self._durations) if self._durations else 0
        total_rows = sum(self._rows_processed)
        error_rate = len(self._errors) / max(len(self._durations), 1)
        return {
            "total_runs": len(self._durations),
            "avg_duration_s": round(avg_duration, 2),
            "total_rows_processed": total_rows,
            "error_rate": round(error_rate, 4),
            "recent_errors": self._errors[-5:],
            "throughput_rows_per_sec": round(total_rows / (sum(self._durations) or 1), 2),
        }

metrics_collector = MetricsCollector()
