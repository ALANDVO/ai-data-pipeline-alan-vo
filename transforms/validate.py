import logging
from typing import List, Dict, Any, Optional

from transforms.llm import pipeline_llm

logger = logging.getLogger(__name__)

class SchemaValidator:
    '''Schema validation with LLM-powered inference and data quality assessment.'''

    async def infer_schema(self, sample_rows: List[Dict[str, Any]], connector_type: str = "postgres") -> Dict[str, Any]:
        result = await pipeline_llm.infer_schema(sample_rows, connector_type)
        logger.info("Inferred schema with %d fields (confidence: %.2f)", len(result.get("fields", [])), result.get("confidence", 0))
        return result

    async def detect_anomalies(self, sample_rows: List[Dict[str, Any]]) -> Dict[str, Any]:
        result = await pipeline_llm.detect_anomalies(sample_rows)
        logger.info("Anomaly detection: %d anomalies (confidence: %.2f)", len(result.get("anomalies", [])), result.get("confidence", 0))
        return result

    def validate_rows(self, rows: List[Dict[str, Any]], schema: List[Dict[str, Any]]) -> Dict[str, Any]:
        if not schema:
            return {"valid": True, "errors": [], "warnings": [], "valid_rows": len(rows)}
        field_map = {f["name"]: f for f in schema}
        errors = []
        warnings = []
        for i, row in enumerate(rows[:1000]):
            for field in schema:
                fname = field["name"]
                if fname not in row:
                    if not field.get("nullable", True):
                        errors.append(f"Row {i}: missing required field '{fname}'")
                    continue
                value = row[fname]
                if value is None:
                    continue
                expected = field.get("type", "string")
                if expected == "integer" and not isinstance(value, (int, float)):
                    errors.append(f"Row {i}: field '{fname}' expected integer, got {type(value).__name__}")
                elif expected == "float" and not isinstance(value, (int, float)):
                    warnings.append(f"Row {i}: field '{fname}' expected float, got {type(value).__name__}")
                elif expected == "boolean" and not isinstance(value, bool):
                    warnings.append(f"Row {i}: field '{fname}' expected boolean, got {type(value).__name__}")
        return {"valid": len(errors) == 0, "errors": errors[:50], "warnings": warnings[:50], "valid_rows": len(rows)}

    def assess_quality(self, rows: List[Dict[str, Any]], schema: List[Dict[str, Any]]) -> Dict[str, Any]:
        completeness = self._completeness(rows, schema)
        accuracy = self._accuracy(rows, schema)
        consistency = self._consistency(rows, schema)
        timeliness = self._timeliness(rows)
        overall = (completeness + accuracy + consistency + timeliness) / 4
        return {
            "completeness": round(completeness, 4),
            "accuracy": round(accuracy, 4),
            "consistency": round(consistency, 4),
            "timeliness": round(timeliness, 4),
            "overall": round(overall, 4),
        }

    def _completeness(self, rows, schema) -> float:
        if not rows or not schema:
            return 0.0
        total_cells = 0
        non_null = 0
        for row in rows[:500]:
            for field in schema:
                total_cells += 1
                if row.get(field["name"]) is not None:
                    non_null += 1
        return non_null / total_cells if total_cells else 0.0

    def _accuracy(self, rows, schema) -> float:
        if not rows or not schema:
            return 1.0
        total = 0
        valid = 0
        for row in rows[:500]:
            for field in schema:
                value = row.get(field["name"])
                if value is None:
                    continue
                total += 1
                etype = field.get("type", "string")
                if etype == "integer" and isinstance(value, (int, float)):
                    valid += 1
                elif etype == "float" and isinstance(value, (int, float)):
                    valid += 1
                elif etype == "boolean" and isinstance(value, bool):
                    valid += 1
                else:
                    valid += 1
        return valid / total if total else 1.0

    def _consistency(self, rows, schema) -> float:
        if len(rows) < 2 or not schema:
            return 1.0
        field_count = len(schema)
        consistent = 0
        for field in schema:
            types = set()
            for row in rows[:200]:
                v = row.get(field["name"])
                if v is not None:
                    types.add(type(v).__name__)
            if len(types) <= 1:
                consistent += 1
        return consistent / field_count if field_count else 1.0

    def _timeliness(self, rows) -> float:
        if not rows:
            return 0.0
        import time
        now = time.time()
        timestamped = 0
        recent = 0
        for row in rows[:200]:
            ts = row.get("timestamp") or row.get("created_at") or row.get("updated_at")
            if ts is not None:
                timestamped += 1
                try:
                    ts_val = float(ts)
                    if now - ts_val < 86400:
                        recent += 1
                except (ValueError, TypeError):
                    recent += 0.5
        if timestamped == 0:
            return 0.5
        freshness = recent / timestamped
        coverage = timestamped / len(rows)
        return (freshness * 0.6 + coverage * 0.4)

schema_validator = SchemaValidator()
