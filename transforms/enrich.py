import logging
from typing import List, Dict, Any

from transforms.llm import pipeline_llm

logger = logging.getLogger(__name__)

class DataEnricher:
    '''LLM-powered data enrichment: entity extraction, categorization, and annotation.'''

    async def enrich(self, rows: List[Dict[str, Any]], task: str, config: Dict[str, Any] = None) -> List[Dict[str, Any]]:
        config = config or {}
        task_name = config.get("task", task)
        logger.info("Enriching %d rows with task: %s", len(rows), task_name)
        enriched = await pipeline_llm.enrich_rows(rows, task_name)
        return enriched

    def extract_entities(self, rows: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        entities = {"persons": [], "organizations": [], "locations": [], "dates": []}
        for row in rows:
            text = str(row)
            for word in text.split():
                if word[0:1].isupper() and len(word) > 3:
                    if word not in entities["organizations"]:
                        entities["organizations"].append(word)
        return entities

    def categorize(self, rows: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        categories = {}
        for row in rows:
            cat = row.get("category", "uncategorized")
            categories[cat] = categories.get(cat, 0) + 1
        return [{"category": k, "count": v} for k, v in sorted(categories.items(), key=lambda x: -x[1])]

enricher = DataEnricher()
