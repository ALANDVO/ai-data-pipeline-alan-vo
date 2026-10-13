import time, logging
from typing import List, Dict, Any, Optional
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)

class QualityScorer:
    '''Data quality scoring: completeness, accuracy, consistency, timeliness.'''

    def __init__(self):
        self.scores: List[Dict[str, Any]] = []
        self._seed_demo()

    def _seed_demo(self):
        now = time.time()
        self.scores = [
            {"pipeline_id": "pipe-demo-orders", "dataset": "orders", "completeness": 0.94, "accuracy": 0.97, "consistency": 0.92, "timeliness": 0.88, "overall": 0.93, "issues": ["3.2% null values in 'email' field", "12 inconsistent date formats"], "scored_at": now - 3600},
            {"pipeline_id": "pipe-demo-logs", "dataset": "server_logs", "completeness": 0.87, "accuracy": 0.91, "consistency": 0.85, "timeliness": 0.95, "overall": 0.90, "issues": ["230 malformed log entries", "5% missing severity levels"], "scored_at": now - 1800},
            {"pipeline_id": "pipe-demo-orders", "dataset": "orders", "completeness": 0.96, "accuracy": 0.98, "consistency": 0.94, "timeliness": 0.91, "overall": 0.95, "issues": ["0.8% duplicate order IDs"], "scored_at": now - 7200},
        ]

    def score(self, pipeline_id: str, dataset: str, metrics: Dict[str, Any]) -> Dict[str, Any]:
        completeness = metrics.get("completeness", 0)
        accuracy = metrics.get("accuracy", 0)
        consistency = metrics.get("consistency", 0)
        timeliness = metrics.get("timeliness", 0)
        overall = (completeness + accuracy + consistency + timeliness) / 4
        issues = metrics.get("issues", [])
        score = {
            "pipeline_id": pipeline_id,
            "dataset": dataset,
            "completeness": round(completeness, 4),
            "accuracy": round(accuracy, 4),
            "consistency": round(consistency, 4),
            "timeliness": round(timeliness, 4),
            "overall": round(overall, 4),
            "issues": issues,
            "scored_at": time.time(),
        }
        self.scores.append(score)
        if len(self.scores) > 500:
            self.scores = self.scores[-500:]
        logger.info("Quality score for %s/%s: %.4f", pipeline_id, dataset, overall)
        return score

    def get_scores(self, pipeline_id: Optional[str] = None, limit: int = 50) -> List[Dict[str, Any]]:
        scores = list(self.scores)
        if pipeline_id:
            scores = [s for s in scores if s["pipeline_id"] == pipeline_id]
        scores.sort(key=lambda s: s["scored_at"], reverse=True)
        return scores[:limit]

    def get_summary(self) -> Dict[str, Any]:
        if not self.scores:
            return {"avg_overall": 0, "total_scored": 0, "lowest": None, "highest": None}
        avg = sum(s["overall"] for s in self.scores) / len(self.scores)
        lowest = min(self.scores, key=lambda s: s["overall"])
        highest = max(self.scores, key=lambda s: s["overall"])
        return {
            "avg_overall": round(avg, 4),
            "total_scored": len(self.scores),
            "lowest": {"pipeline": lowest["pipeline_id"], "dataset": lowest["dataset"], "score": lowest["overall"]},
            "highest": {"pipeline": highest["pipeline_id"], "dataset": highest["dataset"], "score": highest["overall"]},
        }

quality_scorer = QualityScorer()
