import logging
from typing import List, Dict, Any, Optional

from backend.app.services.connectors.base import BaseConnector
from backend.app.core.config import settings

logger = logging.getLogger(__name__)

class PostgresConnector(BaseConnector):
    '''PostgreSQL connector for query, upsert, and CDC support.'''

    def __init__(self):
        super().__init__("postgres", "PostgreSQL")
        self._conn = None

    def _get_conn(self):
        if self._conn is None or self._conn.closed:
            import psycopg2
            self._conn = psycopg2.connect(
                host=settings.postgres_host,
                port=settings.postgres_port,
                dbname=settings.postgres_db,
                user=settings.postgres_user,
                password=settings.postgres_password,
            )
        return self._conn

    def list_objects(self, prefix: str = "") -> List[Dict[str, Any]]:
        conn = self._get_conn()
        with conn.cursor() as cur:
            cur.execute('''
                SELECT table_name FROM information_schema.tables
                WHERE table_schema = 'public' ORDER BY table_name
            ''')
            return [{"name": row[0], "type": "table"} for row in cur.fetchall()]

    def read(self, path: str) -> List[Dict]:
        '''Execute a SQL query and return rows as dicts.'''
        conn = self._get_conn()
        with conn.cursor(name="query_cursor") as cur:
            cur.execute(path)
            columns = [desc[0] for desc in cur.description]
            rows = []
            for row in cur:
                rows.append(dict(zip(columns, row)))
        return rows

    def write(self, path: str, data: Any) -> bool:
        '''Execute an INSERT or UPSERT statement.'''
        conn = self._get_conn()
        with conn.cursor() as cur:
            cur.execute(path, data if isinstance(data, (tuple, list)) else (data,))
        conn.commit()
        logger.info("Executed write in Postgres: %s", path[:80])
        return True

    def upsert(self, table: str, data: Dict, key_columns: List[str]) -> bool:
        '''Perform an upsert (INSERT ... ON CONFLICT UPDATE).'''
        columns = list(data.keys())
        col_str = ", ".join(columns)
        placeholders = ", ".join(["%s"] * len(columns))
        conflict = ", ".join(key_columns)
        update_str = ", ".join([f"{c}=EXCLUDED.{c}" for c in columns if c not in key_columns])
        sql = f"INSERT INTO {table} ({col_str}) VALUES ({placeholders}) ON CONFLICT ({conflict}) DO UPDATE SET {update_str}"
        return self.write(sql, tuple(data.values()))

    def get_schema(self, path: str = "") -> List[Dict[str, Any]]:
        conn = self._get_conn()
        with conn.cursor() as cur:
            cur.execute('''
                SELECT column_name, data_type, is_nullable
                FROM information_schema.columns
                WHERE table_name = %s ORDER BY ordinal_position
            ''', (path,))
            return [
                {"name": row[0], "type": row[1], "nullable": row[2] == "YES"}
                for row in cur.fetchall()
            ]

    def get_cdc_changes(self, table: str, since: str) -> List[Dict]:
        '''Fetch rows modified after a given timestamp (simple CDC).'''
        sql = f"SELECT * FROM {table} WHERE updated_at > %s ORDER BY updated_at"
        return self.read(sql)

postgres_connector = PostgresConnector()
