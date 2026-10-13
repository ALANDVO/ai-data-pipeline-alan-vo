import logging, json
from typing import Optional, Dict, Any, List
import httpx

from backend.app.core.config import settings

logger = logging.getLogger(__name__)

class PipelineLLM:
    '''LLM integration for schema inference, anomaly detection, and data enrichment.'''

    def __init__(self):
        self.base_url = settings.llm_base_url.rstrip("/")
        self.api_key = settings.llm_api_key
        self.model = settings.llm_model

    async def _chat(self, system: str, user: str, temperature: float = 0.2) -> str:
        async with httpx.AsyncClient(timeout=60) as client:
            resp = await client.post(
                f"{self.base_url}/chat/completions",
                headers={"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"},
                json={"model": self.model, "temperature": temperature, "max_tokens": 1500,
                      "messages": [{"role": "system", "content": system}, {"role": "user", "content": user}]},
            )
            resp.raise_for_status()
            data = resp.json()
            return data["choices"][0]["message"]["content"]

    def _parse_json(self, raw: str) -> Dict[str, Any]:
        cleaned = raw.strip().removeprefix("```json").removeprefix("```").removesuffix("```").strip()
        return json.loads(cleaned)

    async def infer_schema(self, sample_rows: List[Dict[str, Any]], connector_type: str = "postgres") -> Dict[str, Any]:
        system = (
            "You are a data engineering expert. Analyze the sample rows and infer the schema. "
            "For each field, determine: name, type (string/integer/float/boolean/date/datetime/json), "
            "nullable (bool), description (one line). Identify the likely primary key. "
            "Return JSON: {fields: [...], primary_key: str|null, confidence: 0.0-1.0}"
        )
        sample = json.dumps(sample_rows[:10], default=str)[:3000]
        user = f"Connector type: {connector_type}\nSample rows:\n{sample}"
        try:
            raw = await self._chat(system, user)
            result = self._parse_json(raw)
            result["inferred_at"] = __import__("time").time()
            result.setdefault("confidence", 0.85)
            return result
        except Exception as e:
            logger.warning("LLM schema inference failed: %s", e)
            return self._local_infer(sample_rows)

    def _local_infer(self, rows: List[Dict]) -> Dict[str, Any]:
        import time
        fields = []
        if rows:
            keys = list(rows[0].keys())
            for key in keys:
                types = {type(r.get(key)).__name__ for r in rows[:50] if r.get(key) is not None}
                type_map = {"int": "integer", "float": "float", "bool": "boolean", "str": "string", "datetime": "datetime"}
                inferred = "string"
                for t in types:
                    if t in type_map:
                        inferred = type_map[t]
                        break
                fields.append({"name": key, "type": inferred, "nullable": True, "description": f"Field {key}", "sample_values": [str(rows[0].get(key))[:50] if rows[0].get(key) is not None else "null"]})
        return {"fields": fields, "primary_key": None, "inferred_at": time.time(), "confidence": 0.6}

    async def detect_anomalies(self, sample_rows: List[Dict[str, Any]]) -> Dict[str, Any]:
        import time
        system = (
            "You are a data quality analyst. Examine the sample rows and identify anomalies: "
            "outliers, inconsistent types, suspicious values, missing patterns. "
            "Return JSON: {detected: bool, anomalies: [{field, issue, severity, count}], summary: str, confidence: 0.0-1.0}"
        )
        sample = json.dumps(sample_rows[:50], default=str)[:4000]
        user = f"Sample data:\n{sample}"
        try:
            raw = await self._chat(system, user)
            result = self._parse_json(raw)
            return result
        except Exception as e:
            logger.warning("LLM anomaly detection failed: %s", e)
            return self._local_anomaly_check(sample_rows)

    def _local_anomaly_check(self, rows: List[Dict]) -> Dict[str, Any]:
        import time
        anomalies = []
        if not rows:
            return {"detected": False, "anomalies": [], "summary": "No data", "confidence": 0.9, "inferred_at": time.time()}
        for key in rows[0].keys():
            nulls = sum(1 for r in rows if r.get(key) is None)
            if nulls > len(rows) * 0.3:
                anomalies.append({"field": key, "issue": f"High null rate ({nulls}/{len(rows)})", "severity": "medium", "count": nulls})
        return {"detected": len(anomalies) > 0, "anomalies": anomalies, "summary": f"Found {len(anomalies)} potential anomalies", "confidence": 0.7}

    async def enrich_rows(self, rows: List[Dict[str, Any]], task: str) -> List[Dict[str, Any]]:
        system = (
            f"You are a data enrichment engine. Task: {task}. "
            "For each row, add an 'enrichment' key with the result. "
            "Return the enriched rows as JSON array."
        )
        sample = json.dumps(rows[:20], default=str)[:3000]
        user = f"Rows to enrich:\n{sample}"
        try:
            raw = await self._chat(system, user)
            result = self._parse_json(raw)
            if isinstance(result, list):
                return result
            return rows
        except Exception as e:
            logger.warning("LLM enrichment failed: %s", e)
            return [{**r, "enrichment": "unavailable"} for r in rows]

pipeline_llm = PipelineLLM()
