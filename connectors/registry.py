import logging
from typing import List, Dict, Any, Optional

logger = logging.getLogger(__name__)

class ConnectorRegistry:
    def __init__(self):
        self._connectors: Dict[str, Any] = {}
        self._register_defaults()

    def _register_defaults(self):
        from connectors.s3 import s3_connector
        from connectors.gcs import gcs_connector
        from connectors.bigquery import bigquery_connector
        from connectors.postgres import postgres_connector
        self._connectors["s3"] = s3_connector
        self._connectors["gcs"] = gcs_connector
        self._connectors["bigquery"] = bigquery_connector
        self._connectors["postgres"] = postgres_connector

    def get(self, connector_type: str):
        connector = self._connectors.get(connector_type)
        if not connector:
            raise ValueError(f"Unknown connector type: {connector_type}")
        return connector

    def list_connectors(self) -> List[Dict[str, Any]]:
        results = []
        for ctype, connector in self._connectors.items():
            try:
                health = connector.health_check()
                results.append({
                    "type": ctype, "name": connector.name,
                    "status": health.get("status", "unknown"),
                    "config_summary": {"type": ctype, "name": connector.name},
                })
            except Exception as e:
                results.append({
                    "type": ctype, "name": connector.name,
                    "status": "error",
                    "config_summary": {"type": ctype, "error": str(e)},
                })
        return results

connector_registry = ConnectorRegistry()
