"""Data quality scoring with persistent SQLite storage."""
import json
import time
import logging
from typing import List, Dict, Any, Optional

from backend.app.core.database import get_db
from backend.app.models.database import QualityScoreModel

logger = logging.getLogger(__name__)


class QualityScorer:
    """Data quality scoring: completeness, accuracy, consistency, timeliness."""

    def __init__(self):
        self._seed_demo()

    def _seed_demo(self):
        with get_db() as db:
            count = db.query(QualityScoreModel).count()
            if count == 0:
                now = time.time()
                scores = [
                    QualityScoreModel(
                        pipeline_id="pipe-demo-orders", dataset_name="orders",
                        completeness=0.94, accuracy=0.97, consistency=0.92, timeliness=0.88, overall=0.93,
                        details=json.dumps({"issues": ["3.2% null values in 'email' field", "12 inconsistent date formats"]}),
                        created_at=now - 3600,
                    ),
                    QualityScoreModel(
                        pipeline_id="pipe-demo-logs", dataset_name="server_logs",
                        completeness=0.87, accuracy=0.91, consistency=0.85, timeliness=0.95, overall=0.90,
                        details=json.dumps({"issues": ["230 malformed log entries", "5% missing severity levels"]}),
                        created_at=now - 1800,
                    ),
                    QualityScoreModel(
                        pipeline_id="pipe-demo-orders", dataset_name="orders",
                        completeness=0.96, accuracy=0.98, consistency=0.94, timeliness=0.91, overall=0.95,
                        details=json.dumps({"issues": ["0.8% duplicate order IDs"]}),
                        created_at=now - 7200,
                    ),
                ]
                for s in scores:
                    db.add(s)
                db.commit()
                logger.info("Seeded demo quality scores")

    def score(self, pipeline_id: str, dataset: str, metrics: Dict[str, Any]) -> Dict[str, Any]:
        completeness = metrics.get("completeness", 0)
        accuracy = metrics.get("accuracy", 0)
        consistency = metrics.get("consistency", 0)
        timeliness = metrics.get("timeliness", 0)
        overall = (completeness + accuracy + consistency + timeliness) / 4
        issues = metrics.get("issues", [])

        score_model = QualityScoreModel(
            pipeline_id=pipeline_id,
            dataset_name=dataset,
            completeness=round(completeness, 4),
            accuracy=round(accuracy, 4),
            consistency=round(consistency, 4),
            timeliness=round(timeliness, 4),
            overall=round(overall, 4),
            details=json.dumps({"issues": issues}),
            created_at=time.time(),
        )

        with get_db() as db:
            db.add(score_model)
            db.commit()
            db.refresh(score_model)

        logger.info("Quality score for %s/%s: %.4f", pipeline_id, dataset, overall)
        return self._to_dict(score_model)

    def get_scores(self, pipeline_id: Optional[str] = None, limit: int = 50) -> List[Dict[str, Any]]:
        with get_db() as db:
            query = db.query(QualityScoreModel)
            if pipeline_id:
                query = query.filter(QualityScoreModel.pipeline_id == pipeline_id)
            scores = query.order_by(QualityScoreModel.created_at.desc()).limit(limit).all()
            return [self._to_dict(s) for s in scores]

    def get_summary(self) -> Dict[str, Any]:
        with get_db() as db:
            scores = db.query(QualityScoreModel).all()
            if not scores:
                return {"avg_overall": 0, "total_scored": 0, "lowest": None, "highest": None}
            avg = sum(s.overall for s in scores) / len(scores)
            lowest = min(scores, key=lambda s: s.overall)
            highest = max(scores, key=lambda s: s.overall)
            return {
                "avg_overall": round(avg, 4),
                "total_scored": len(scores),
                "lowest": {"pipeline": lowest.pipeline_id, "dataset": lowest.dataset_name, "score": lowest.overall},
                "highest": {"pipeline": highest.pipeline_id, "dataset": highest.dataset_name, "score": highest.overall},
            }

    @staticmethod
    def _to_dict(model: QualityScoreModel) -> Dict[str, Any]:
        details = {}
        if model.details:
            try:
                details = json.loads(model.details)
            except json.JSONDecodeError:
                details = {}
        return {
            "pipeline_id": model.pipeline_id,
            "dataset": model.dataset_name,
            "completeness": model.completeness,
            "accuracy": model.accuracy,
            "consistency": model.consistency,
            "timeliness": model.timeliness,
            "overall": model.overall,
            "issues": details.get("issues", []),
            "scored_at": model.created_at,
        }


quality_scorer = QualityScorer()