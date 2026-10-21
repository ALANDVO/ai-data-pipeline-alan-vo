"""Job scheduler with persistent SQLite storage."""
import time
import logging
import random
from typing import List, Dict, Any, Optional
from concurrent.futures import ThreadPoolExecutor

from backend.app.models.schemas import JobRecord, TaskRecord
from backend.app.services.orchestrator.pipeline import DAGValidator
from backend.app.services.monitoring.metrics import metrics_collector
from backend.app.core.database import get_db
from backend.app.models.database import JobModel, TaskModel

logger = logging.getLogger(__name__)


class RetryConfig:
    def __init__(self, max_retries: int = 3, base_delay: float = 1.0, max_delay: float = 30.0):
        self.max_retries = max_retries
        self.base_delay = base_delay
        self.max_delay = max_delay

    def delay(self, attempt: int) -> float:
        delay = self.base_delay * (2 ** attempt)
        jitter = random.uniform(0, delay * 0.1)
        return min(delay + jitter, self.max_delay)


class JobScheduler:
    def __init__(self, max_workers: int = 4, retry_config: Optional[RetryConfig] = None):
        self.retry_config = retry_config or RetryConfig()
        self._executor = ThreadPoolExecutor(max_workers=max_workers)
        self._task_handlers: Dict[str, callable] = {}

    def register_handler(self, task_type: str, handler: callable):
        self._task_handlers[task_type] = handler

    def submit(self, pipeline_id: str, triggered_by: str = "") -> Dict[str, Any]:
        from backend.app.services.orchestrator.engine import pipeline_engine

        pipeline = pipeline_engine.get_pipeline(pipeline_id)
        if not pipeline:
            raise ValueError(f"Pipeline {pipeline_id} not found")

        validator = DAGValidator()
        validation = validator.validate(pipeline["nodes"], pipeline["edges"])
        if not validation["valid"]:
            raise ValueError(f"Invalid DAG: {validation['errors']}")

        job_id = f"job-{int(time.time() * 1000)}-{random.randint(1000, 9999)}"
        now = time.time()

        job_model = JobModel(
            id=job_id, pipeline_id=pipeline_id, status="running",
            triggered_by=triggered_by, started_at=now,
        )

        with get_db() as db:
            db.add(job_model)
            db.commit()
            # Extract data before session closes
            job_data = {
                "id": job_model.id,
                "pipeline_id": job_model.pipeline_id,
                "status": job_model.status,
                "triggered_by": job_model.triggered_by,
                "started_at": job_model.started_at,
                "completed_at": job_model.completed_at,
                "duration_ms": job_model.duration_ms,
                "tasks": [],
                "error": job_model.error,
            }

        levels = validation["topological_levels"]
        self._executor.submit(self._run_pipeline, job_id, levels, pipeline)

        return job_data

    def _run_pipeline(self, job_id: str, levels: List[List[str]], pipeline: Dict[str, Any]):
        with get_db() as db:
            job = db.query(JobModel).filter(JobModel.id == job_id).first()
            if not job:
                logger.error("Job %s not found", job_id)
                return

        nodes_by_id = {n["id"]: n for n in pipeline["nodes"]}
        completed_tasks = set()

        for level in levels:
            for task_id in level:
                node = nodes_by_id.get(task_id)
                if not node:
                    continue

                task_model = TaskModel(
                    task_id=task_id, job_id=job_id, status="running",
                )
                with get_db() as db:
                    db.add(task_model)
                    db.commit()

                handler = self._task_handlers.get(node.get("type"), self._default_handler)
                start = time.time()

                try:
                    result = self._execute_with_retry(task_model, handler, node, pipeline)
                    task_model.status = "completed"
                    task_model.duration_ms = (time.time() - start) * 1000
                    task_model.set_output(result)
                    completed_tasks.add(task_id)
                except Exception as e:
                    logger.exception("Task %s failed: %s", task_id, e)
                    task_model.status = "failed"
                    task_model.error = str(e)
                    task_model.duration_ms = (time.time() - start) * 1000

                    with get_db() as db:
                        job = db.query(JobModel).filter(JobModel.id == job_id).first()
                        if job:
                            job.status = "failed"
                            job.error = f"Task {task_id} failed: {e}"
                            job.completed_at = time.time()
                            job.duration_ms = (job.completed_at - job.started_at) * 1000
                            db.commit()
                    return

                with get_db() as db:
                    db.merge(task_model)
                    db.commit()

        with get_db() as db:
            job = db.query(JobModel).filter(JobModel.id == job_id).first()
            if job:
                job.status = "completed"
                job.completed_at = time.time()
                job.duration_ms = (job.completed_at - job.started_at) * 1000
                db.commit()

        metrics_collector.record_job_completion(job_id, pipeline["id"], "completed")
        pipeline_engine.update_pipeline_status(pipeline["id"], "completed")

    def _execute_with_retry(self, task: TaskModel, handler: callable, node: Dict, pipeline: Dict) -> Dict[str, Any]:
        attempt = 0
        while attempt <= self.retry_config.max_retries:
            try:
                return handler(node, pipeline)
            except Exception as e:
                if attempt >= self.retry_config.max_retries:
                    raise
                task.retries = attempt + 1
                task.status = "retrying"
                delay = self.retry_config.delay(attempt)
                logger.warning("Task %s retry %d/%d after %.1fs: %s", task.task_id, attempt + 1, self.retry_config.max_retries, delay, e)
                time.sleep(delay)
                attempt += 1

    def _default_handler(self, node: Dict, pipeline: Dict) -> Dict[str, Any]:
        logger.info("Executing task %s (type=%s) in pipeline %s", node.get("id"), node.get("type"), pipeline.get("id"))
        return {"rows_processed": 0, "node": node.get("id"), "type": node.get("type")}

    def get_jobs(self, status: Optional[str] = None, pipeline_id: Optional[str] = None, limit: int = 100) -> List[Dict]:
        with get_db() as db:
            query = db.query(JobModel)
            if status:
                query = query.filter(JobModel.status == status)
            if pipeline_id:
                query = query.filter(JobModel.pipeline_id == pipeline_id)
            jobs = query.order_by(JobModel.started_at.desc()).limit(limit).all()
            return [self._job_to_dict(j) for j in jobs]

    def get_job(self, job_id: str) -> Optional[Dict]:
        with get_db() as db:
            job = db.query(JobModel).filter(JobModel.id == job_id).first()
            return self._job_to_dict(job) if job else None

    def retry(self, job_id: str, triggered_by: str = "") -> Dict[str, Any]:
        with get_db() as db:
            job = db.query(JobModel).filter(JobModel.id == job_id).first()
            if not job:
                raise ValueError(f"Job {job_id} not found")
            pipeline_id = job.pipeline_id

        return self.submit(pipeline_id, triggered_by=f"{triggered_by} (retry)")

    def _job_to_dict(self, job: JobModel) -> Dict[str, Any]:
        return {
            "id": job.id, "pipeline_id": job.pipeline_id,
            "status": job.status, "triggered_by": job.triggered_by,
            "started_at": job.started_at, "completed_at": job.completed_at,
            "duration_ms": job.duration_ms,
            "tasks": [
                {"task_id": t.task_id, "status": t.status, "rows_processed": t.rows_processed,
                 "duration_ms": t.duration_ms, "error": t.error, "retries": t.retries,
                 "output": t.get_output()}
                for t in job.tasks
            ],
            "error": job.error,
        }


job_scheduler = JobScheduler()