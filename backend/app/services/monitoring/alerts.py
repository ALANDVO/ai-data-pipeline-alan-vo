import logging
from typing import List, Dict, Any, Optional

logger = logging.getLogger(__name__)

class AlertRule:
    def __init__(self, name: str, metric: str, operator: str, threshold: float, severity: str):
        self.name = name
        self.metric = metric
        self.operator = operator
        self.threshold = threshold
        self.severity = severity

class AlertEvaluator:
    def __init__(self):
        self.rules: List[AlertRule] = [
            AlertRule("high_error_rate", "error_rate", ">", 0.1, "critical"),
            AlertRule("slow_pipeline", "avg_duration_s", ">", 10.0, "warning"),
            AlertRule("low_quality", "quality_score", "<", 0.7, "warning"),
            AlertRule("high_null_rate", "null_rate", ">", 0.2, "warning"),
        ]
        self.alerts: List[Dict[str, Any]] = []

    def evaluate(self, metrics: Dict[str, Any]) -> List[Dict[str, Any]]:
        triggered = []
        for rule in self.rules:
            value = metrics.get(rule.metric)
            if value is None:
                continue
            fired = self._check(rule.operator, value, rule.threshold)
            if fired:
                alert = {
                    "rule": rule.name,
                    "metric": rule.metric,
                    "value": value,
                    "threshold": rule.threshold,
                    "severity": rule.severity,
                    "message": f"{rule.name}: {rule.metric}={value} {rule.operator} {rule.threshold}",
                }
                triggered.append(alert)
                self.alerts.append(alert)
                logger.warning("ALERT [%s] %s", rule.severity.upper(), rule.name)
        return triggered

    def _check(self, operator: str, value: float, threshold: float) -> bool:
        if operator == ">":
            return value > threshold
        if operator == "<":
            return value < threshold
        if operator == ">=":
            return value >= threshold
        if operator == "<=":
            return value <= threshold
        return False

    def get_alerts(self, limit: int = 50) -> List[Dict[str, Any]]:
        return self.alerts[-limit:]

alert_evaluator = AlertEvaluator()
