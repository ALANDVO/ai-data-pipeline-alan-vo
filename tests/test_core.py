import pytest
import time

from orchestrator.pipeline import DAGValidator
from orchestrator.engine import pipeline_engine
from orchestrator.scheduler import JobScheduler, RetryConfig
from transforms.clean import data_cleaner
from transforms.validate import schema_validator
from monitoring.quality import quality_scorer
from monitoring.alerts import alert_evaluator
from utils.helpers import generate_id, chunk_list

def test_dag_validator_valid():
    validator = DAGValidator()
    nodes = [{"id": "a"}, {"id": "b"}, {"id": "c"}]
    edges = [{"id": "e1", "source": "a", "target": "b"}, {"id": "e2", "source": "b", "target": "c"}]
    result = validator.validate(nodes, edges)
    assert result["valid"] is True
    assert result["topological_order"] == ["a", "b", "c"]

def test_dag_validator_cycle():
    validator = DAGValidator()
    nodes = [{"id": "a"}, {"id": "b"}]
    edges = [{"id": "e1", "source": "a", "target": "b"}, {"id": "e2", "source": "b", "target": "a"}]
    result = validator.validate(nodes, edges)
    assert result["valid"] is False
    assert any("cycle" in e.lower() for e in result["errors"])

def test_dag_execution_groups():
    validator = DAGValidator()
    nodes = [{"id": "a"}, {"id": "b"}, {"id": "c"}, {"id": "d"}]
    edges = [
        {"id": "e1", "source": "a", "target": "b"},
        {"id": "e2", "source": "a", "target": "c"},
        {"id": "e3", "source": "b", "target": "d"},
        {"id": "e4", "source": "c", "target": "d"},
    ]
    levels = validator.get_execution_groups(nodes, edges)
    assert levels[0] == ["a"]
    assert set(levels[1]) == {"b", "c"}
    assert levels[2] == ["d"]

def test_pipeline_engine_seed():
    pipelines = pipeline_engine.get_pipelines()
    assert len(pipelines) >= 2
    assert any(p["name"] == "Orders ETL Pipeline" for p in pipelines)

def test_data_cleaner_dedup():
    rows = [
        {"id": 1, "name": "Alice"},
        {"id": 2, "name": "Bob"},
        {"id": 1, "name": "Alice"},
    ]
    result = data_cleaner.clean(rows, {"dedup": True, "key_columns": ["id"]})
    assert result["rows_processed"] == 2
    assert result["rows_removed"] == 1

def test_data_cleaner_nulls():
    rows = [{"a": 1, "b": None}, {"a": None, "b": 2}]
    result = data_cleaner.clean(rows, {"nulls": "fill", "fill_value": 0})
    assert result["rows"][0]["b"] == 0
    assert result["rows"][1]["a"] == 0

def test_data_cleaner_coerce():
    rows = [{"age": "25", "score": "3.7"}]
    result = data_cleaner.clean(rows, {"schema": {"age": "integer", "score": "float"}})
    assert result["rows"][0]["age"] == 25
    assert result["rows"][0]["score"] == 3.7

def test_retry_config_backoff():
    config = RetryConfig(max_retries=3, base_delay=1.0, max_delay=30.0)
    assert config.delay(0) >= 1.0
    assert config.delay(1) >= 2.0
    assert config.delay(5) <= 30.0

def test_quality_scorer_seed():
    scores = quality_scorer.get_scores()
    assert len(scores) >= 3
    assert all(0 <= s["overall"] <= 1 for s in scores)

def test_quality_scorer_score():
    score = quality_scorer.score("test-pipe", "test-dataset", {
        "completeness": 0.9, "accuracy": 0.8, "consistency": 0.7, "timeliness": 0.6
    })
    assert score["overall"] == pytest.approx(0.75, abs=0.01)

def test_alert_evaluator():
    metrics = {"error_rate": 0.15, "avg_duration_s": 5.0, "quality_score": 0.8, "null_rate": 0.1}
    alerts = alert_evaluator.evaluate(metrics)
    assert any(a["rule"] == "high_error_rate" for a in alerts)

def test_generate_id():
    id1 = generate_id("test")
    id2 = generate_id("test")
    assert id1.startswith("test-")
    assert id1 != id2

def test_chunk_list():
    assert chunk_list([1, 2, 3, 4, 5], 2) == [[1, 2], [3, 4], [5]]
    assert chunk_list([], 3) == []
