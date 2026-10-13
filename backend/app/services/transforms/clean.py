import logging
from typing import List, Dict, Any, Optional

logger = logging.getLogger(__name__)

class DataCleaner:
    '''Data cleaning transforms: null handling, deduplication, and type coercion.'''

    def handle_nulls(self, rows: List[Dict[str, Any]], strategy: str = "fill", fill_value: Any = None) -> List[Dict[str, Any]]:
        if strategy == "drop":
            return [row for row in rows if all(v is not None for v in row.values())]
        if strategy == "fill":
            return [{k: (fill_value if v is None else v) for k, v in row.items()} for row in rows]
        return rows

    def deduplicate(self, rows: List[Dict[str, Any]], key_columns: Optional[List[str]] = None) -> List[Dict[str, Any]]:
        if key_columns:
            seen = set()
            unique = []
            for row in rows:
                key = tuple(row.get(k) for k in key_columns)
                if key not in seen:
                    seen.add(key)
                    unique.append(row)
            removed = len(rows) - len(unique)
            if removed:
                logger.info("Deduplication removed %d rows (keys: %s)", removed, key_columns)
            return unique
        seen = set()
        unique = []
        for row in rows:
            key = tuple(sorted(row.items()))
            if key not in seen:
                seen.add(key)
                unique.append(row)
        return unique

    def coerce_types(self, rows: List[Dict[str, Any]], schema: Dict[str, str]) -> List[Dict[str, Any]]:
        coerced = []
        for row in rows:
            new_row = {}
            for k, v in row.items():
                target = schema.get(k)
                if v is None:
                    new_row[k] = None
                    continue
                try:
                    if target == "integer":
                        new_row[k] = int(float(v))
                    elif target == "float":
                        new_row[k] = float(v)
                    elif target == "boolean":
                        if isinstance(v, str):
                            new_row[k] = v.lower() in ("true", "1", "yes")
                        else:
                            new_row[k] = bool(v)
                    elif target == "string":
                        new_row[k] = str(v)
                    else:
                        new_row[k] = v
                except (ValueError, TypeError):
                    new_row[k] = v
            coerced.append(new_row)
        return coerced

    def clean(self, rows: List[Dict[str, Any]], config: Dict[str, Any]) -> Dict[str, Any]:
        original_count = len(rows)
        cleaned = rows
        if config.get("nulls") in ("fill", "drop"):
            cleaned = self.handle_nulls(cleaned, config["nulls"], config.get("fill_value"))
        if config.get("dedup"):
            cleaned = self.deduplicate(cleaned, config.get("key_columns"))
        if config.get("schema"):
            cleaned = self.coerce_types(cleaned, config["schema"])
        return {
            "rows": cleaned,
            "rows_processed": len(cleaned),
            "rows_removed": original_count - len(cleaned),
            "config_applied": list(config.keys()),
        }

data_cleaner = DataCleaner()
