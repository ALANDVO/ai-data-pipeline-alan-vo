import logging
from typing import List, Dict, Any, Optional

from connectors.base import BaseConnector
from config import settings

logger = logging.getLogger(__name__)

class BigQueryConnector(BaseConnector):
    '''BigQuery connector for query execution, table export, and schema retrieval.'''

    def __init__(self):
        super().__init__("bigquery", "BigQuery")
        self._client = None
        self._project = settings.bigquery_project
        self._dataset = settings.bigquery_dataset

    def _get_client(self):
        if self._client is None:
            from google.cloud import bigquery
            self._client = bigquery.Client(project=self._project)
        return self._client

    def list_objects(self, prefix: str = "") -> List[Dict[str, Any]]:
        client = self._get_client()
        dataset = f"{self._project}.{self._dataset}"
        tables = list(client.list_tables(dataset))
        return [
            {"name": t.table_id, "type": "table", "created": t.created.isoformat() if t.created else None}
            for t in tables
        ]

    def read(self, path: str) -> List[Dict]:
        '''Execute a SQL query and return rows.'''
        client = self._get_client()
        query = client.query(path)
        return list(client.query(path).result())

    def write(self, path: str, data: Any) -> bool:
        '''Load data into a BigQuery table.'''
        client = self._get_client()
        table_ref = f"{self._project}.{self._dataset}.{path}"
        table = client.get_table(table_ref)
        rows = data if isinstance(data, list) else [data]
        client.insert_rows_json(table, rows)
        logger.info("Loaded %d rows into BigQuery table %s", len(rows), table_ref)
        return True

    def get_schema(self, path: str = "") -> List[Dict[str, Any]]:
        client = self._get_client()
        table_ref = f"{self._project}.{self._dataset}.{path}"
        table = client.get_table(table_ref)
        return [
            {"name": col.name, "type": str(col.field_type), "nullable": col.is_nullable}
            for col in table.schema
        ]

    def export_to_csv(self, query: str, output_path: str) -> str:
        client = self._get_client()
        job_config = bigquery.QueryJobConfig(destination=f"{self._project}.{self._dataset}.export_tmp")
        query_job = client.query(query, job_config=job_config)
        query_job.result()
        destination_table = client.get_table(job_config.destination)
        csv_file = f"gs://{self._bucket}/{output_path}"
        export_config = bigquery.ExtractionConfig(destination_uri=csv_file, destination_format=bigquery.SourceFormat.CSV)
        extract_job = client.extract_table(destination_table, csv_file, configuration=export_config)
        extract_job.result()
        return csv_file

bigquery_connector = BigQueryConnector()
