import time, logging, random
from typing import List, Dict, Any, Optional
from concurrent.futures import ThreadPoolExecutor

from models.schemas import JobRecord, TaskRecord
from orchestrator.pipeline import DAGValidator
from monitoring.metrics import metrics_collector

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
        self.jobs: Dict[str, JobRecord] = {}
        self.executor = ThreadPoolExecutor(max_workers=max_workers)
        self.retry_config = retry_config or RetryConfig()
        self._task_handlers: Dict[str, callable] = {}

    def register_handler(self, task_type: str, handler: callable):
        self._task_handlers[task_type] = handler

    def submit(self, pipeline_id: str, triggered_by: str = "") -> Dict[str, Any]:
        from orchestrator.engine import pipeline_engine
        pipeline = pipeline_engine.get_pipeline(pipeline_id)
        if not pipeline:
            raise ValueError(f"Pipeline {pipeline_id} not found")
        job_id = f"job-{pipeline_id[:8]}-{int(time.time() * 1000)}"
        job = JobRecord(id=job_id, pipeline_id=pipeline_id, triggered_by=triggered_by)
        self.jobs[job_id] = job
        validator = DAGValidator()
        levels = validator.get_execution_groups(pipeline["nodes"], pipeline["edges"])
        future = self.executor.submit(self._run_pipeline, job_id, levels, pipeline)
        job.status = "running"
        job.started_at = time.time()
        metrics_collector.log(job_id=job_id, pipeline_id=pipeline_id, level="info", message=f"Job {job_id} started", source="scheduler")
        return job.to_dict()

    def _run_pipeline(self, job_id: str, levels: List[List[str]], pipeline: Dict[str, Any]):
        job = self.jobs.get(job_id)
        if not job:
            return
        node_map = {n["id"]: n for n in pipeline["nodes"]}
        all_tasks = []
        try:
            for level_idx, level in enumerate(levels):
                level_tasks = []
                for node_id in level:
                    node = node_map[node_id]
                    task = TaskRecord(task_id=node_id)
                    handler = self._task_handlers.get(node["type"], self._default_handler)
                    result = self._execute_with_retry(task, handler, node, pipeline)
                    level_tasks.append(result)
                    all_tasks.append(result)
                job.tasks = list(all_tasks)
            job.status = "completed"
            metrics_collector.log(job_id=job_id, pipeline_id=job.pipeline_id, level="info", message=f"Job {job_id} completed", source="scheduler")
        except Exception as e:
            job.status = "failed"
            job.error = str(e)
            logger.error("Job %s failed: %s", job_id, e)
            metrics_collector.log(job_id=job_id, pipeline_id=job.pipeline_id, level="error", message=f"Job {job_id} failed: {e}", source="scheduler")
        finally:
            job.completed_at = time.time()
            if job.started_at:
                job.duration_ms = (job.completed_at - job.started_at) * 1000

    def _execute_with_retry(self, task: TaskRecord, handler: callable, node: Dict, pipeline: Dict) -> TaskRecord:
        attempt = 0
        while True:
            try:
                start = time.time()
                result = handler(node, pipeline)
                task.status = "completed"
                task.rows_processed = result.get("rows_processed", 0) if isinstance(result, dict) else 0
                task.output = result if isinstance(result, dict) else {"result": result}
                task.duration_ms = (time.time() - start) * 1000
                return task
            except Exception as e:
                task.retries += 1
                if task.retries >= self.retry_config.max_retries:
                    task.status = "failed"
                    task.error = str(e)
                    logger.warning("Task %s failed after %d retries: %s", task.task_id, task.retries, e)
                    return task
                delay = self.retry_config.delay(attempt)
                logger.info("Retrying task %s in %.2fs (attempt %d/%d)", task.task_id, delay, task.retries, self.retry_config.max_retries)
                time.sleep(delay)
                attempt += 1

    def _default_handler(self, node: Dict, pipeline: Dict) -> Dict[str, Any]:
        logger.info("Executing task %s (type=%s) in pipeline %s", node.get("id"), node.get("type"), pipeline.get("id"))
        return {"rows_processed": 0, "node": node.get("id"), "type": node.get("type")}

    def get_jobs(self, status: Optional[str] = None, pipeline_id: Optional[str] = None, limit: int = 100) -> List[Dict]:
        jobs = list(self.jobs.values())
        if status:
            jobs = [j for j in jobs if j.status == status]
        if pipeline_id:
            jobs = [j for j in jobs if j.pipeline_id == pipeline_id]
        jobs.sort(key=lambda j: j.started_at or 0, reverse=True)
        return [j.to_dict() for j in jobs[:limit]]

    def get_job(self, job_id: str) -> Optional[Dict]:
        job = self.jobs.get(job_id)
        return job.to_dict() if job else None

    def retry(self, job_id: str, triggered_by: str = "") -> Dict[str, Any]:
        job = self.jobs.get(job_id)
        if not job:
            raise ValueError(f"Job {job_id} not found")
        if job.status not in ("failed", "completed"):
            raise ValueError(f"Job {job_id} cannot be retried (status={job.status})")
        return self.submit(job.pipeline_id, triggered_by=f"{triggered_by} (retry)")

job_scheduler = JobScheduler()
