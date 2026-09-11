import pytest
from unittest.mock import patch, MagicMock
from starlette.testclient import TestClient
from sqlalchemy import Index, text

from app.main import app
from app.settings import settings
from app.infrastructure.database.models import Question
from app.infrastructure.database.engine import engine, SessionLocal
from app.observability.metrics import metrics_registry, MetricsRegistry
from app.domain.content.validator import validate_question_payload, QuestionValidationError
from app.domain.content.loader import load_track_bundle


@pytest.fixture
def admin_client():
    client = TestClient(app)
    login_res = client.post(
        "/api/v1/admin/login",
        json={"username": settings.admin_username, "password": settings.admin_password},
    )
    assert login_res.status_code == 200
    token = login_res.json()["token"]
    client.headers.update({"Authorization": f"Bearer {token}"})
    return client


def test_question_trigram_indexes_defined():
    """Verify PostgreSQL GIN trigram indexes are declared on Question table for prompt and topic."""
    index_names = [arg.name for arg in Question.__table_args__ if isinstance(arg, Index)]
    assert "ix_ob_questions_prompt_trgm" in index_names
    assert "ix_ob_questions_topic_trgm" in index_names

    prompt_idx = next(arg for arg in Question.__table_args__ if isinstance(arg, Index) and arg.name == "ix_ob_questions_prompt_trgm")
    topic_idx = next(arg for arg in Question.__table_args__ if isinstance(arg, Index) and arg.name == "ix_ob_questions_topic_trgm")

    assert prompt_idx.dialect_options["postgresql"]["using"] == "gin"
    assert prompt_idx.dialect_options["postgresql"]["ops"]["prompt"] == "gin_trgm_ops"

    assert topic_idx.dialect_options["postgresql"]["using"] == "gin"
    assert topic_idx.dialect_options["postgresql"]["ops"]["topic"] == "gin_trgm_ops"


def test_admin_search_questions(admin_client):
    """Verify admin question search filters by prompt and topic."""
    # Search for an existing prompt keyword
    res = admin_client.get("/api/v1/admin/tracks/organic1/questions?search=Which&limit=10")
    assert res.status_code == 200
    data = res.json()
    assert "items" in data
    assert "total" in data
    for item in data["items"]:
        match = ("which" in item["prompt"].lower()) or (item["topic"] and "which" in item["topic"].lower())
        assert match

    # Search for non-existent term
    res_empty = admin_client.get("/api/v1/admin/tracks/organic1/questions?search=XYZNONEXISTENTTERM12345")
    assert res_empty.status_code == 200
    assert res_empty.json()["total"] == 0
    assert len(res_empty.json()["items"]) == 0


def test_admin_search_postgresql_expression():
    """Verify PostgreSQL full-text and trigram query compiles cleanly for postgresql dialect."""
    from sqlalchemy.dialects import postgresql
    from sqlalchemy import func, or_
    clean_search = "esterification"
    ts_query = func.plainto_tsquery("english", clean_search)
    prompt_ts = func.to_tsvector("english", Question.prompt)
    topic_ts = func.to_tsvector("english", func.coalesce(Question.topic, ""))
    filter_expr = or_(
        prompt_ts.bool_op("@@")(ts_query),
        topic_ts.bool_op("@@")(ts_query),
        Question.prompt.ilike(f"%{clean_search}%"),
        Question.topic.ilike(f"%{clean_search}%"),
    )
    compiled = str(filter_expr.compile(dialect=postgresql.dialect()))
    assert "to_tsvector" in compiled
    assert "plainto_tsquery" in compiled
    assert "ILIKE" in compiled


def test_database_query_latency_tracking():
    """Verify executing database queries records query count and latency metrics."""
    metrics_registry.clear()
    initial_metrics = metrics_registry.get_query_latency_metrics()
    assert initial_metrics["total_queries"] == 0

    with SessionLocal() as db:
        db.execute(text("SELECT 1")).all()

    latency_metrics = metrics_registry.get_query_latency_metrics()
    assert latency_metrics["total_queries"] >= 1
    assert latency_metrics["avg_query_latency_ms"] >= 0.0
    assert latency_metrics["max_query_latency_ms"] >= 0.0


def test_connection_pool_utilization_metrics():
    """Verify connection pool utilization is reported across metrics."""
    sys_metrics = metrics_registry.get_system_metrics()
    assert "connection_pool" in sys_metrics
    pool_info = sys_metrics["connection_pool"]
    assert "dialect" in pool_info
    assert "pool_type" in pool_info
    assert "checked_in" in pool_info
    assert "checked_out" in pool_info
    assert "utilization_pct" in pool_info


def test_track_bundle_load_time_and_cache_memory():
    """Verify bundle load time, cache hits/misses, and memory consumption are tracked."""
    from app.api.deps import get_content_bundle
    bundle = get_content_bundle("track:organic1")
    assert bundle is not None

    sys_metrics = metrics_registry.get_system_metrics()

    # 3. Track or boss bundle load time
    assert "bundle_load_time_ms" in sys_metrics
    assert "organic1" in sys_metrics["bundle_load_time_ms"]

    # 4. Cache hits and misses
    assert "cache_hits_misses" in sys_metrics
    assert sys_metrics["cache_hits_misses"]["hits"] >= 0

    # 5. Cache memory consumption
    assert "cache_memory_consumption" in sys_metrics
    assert sys_metrics["cache_memory_consumption"]["total_cache_bytes"] > 0
    assert sys_metrics["cache_memory_consumption"]["total_cache_kb"] > 0
    assert "organic1" in sys_metrics["cache_memory_consumption"]["bundle_sizes_bytes"]


def test_json_fallback_count_metric():
    """Verify JSON fallback events are counted and tracked per track."""
    metrics_registry.clear()
    metrics_registry.record_json_fallback("organic1")
    metrics_registry.record_json_fallback("organic1")
    metrics_registry.record_json_fallback("organic2")

    fallback_metrics = metrics_registry.get_json_fallback_metrics()
    assert fallback_metrics["total_fallback_count"] == 3
    assert fallback_metrics["by_track"]["organic1"] == 2
    assert fallback_metrics["by_track"]["organic2"] == 1


def test_ingestion_validation_failure_metric():
    """Verify ingestion validation failures are captured in metrics."""
    metrics_registry.clear()
    with pytest.raises(QuestionValidationError):
        validate_question_payload(
            options=[{"label": "A", "text": "Only one choice"}],  # invalid: < 2 choices
            correct_option="A",
            correct_answer="Only one choice",
        )

    val_metrics = metrics_registry.get_ingestion_validation_metrics()
    assert val_metrics["total_validation_failures"] >= 1
    assert len(val_metrics["recent_failures"]) >= 1
    assert "choices" in val_metrics["recent_failures"][-1]["error"]


def test_content_version_mismatch_metric():
    """Verify content version mismatches are logged with details."""
    metrics_registry.clear()
    metrics_registry.record_content_version_mismatch(
        track_id="organic1",
        requested_version="v2.0.0",
        active_version="v1.0.0"
    )

    mismatch_metrics = metrics_registry.get_content_version_mismatch_metrics()
    assert mismatch_metrics["total_version_mismatches"] == 1
    assert mismatch_metrics["recent_mismatches"][0]["track_id"] == "organic1"
    assert mismatch_metrics["recent_mismatches"][0]["requested_version"] == "v2.0.0"
    assert mismatch_metrics["recent_mismatches"][0]["active_version"] == "v1.0.0"


def test_combat_concurrency_conflict_metric():
    """Verify concurrent combat conflicts are logged into metrics."""
    metrics_registry.clear()
    metrics_registry.record_combat_concurrency_conflict(
        session_id="sess-123",
        reason="OptimisticLockVersionMismatch: expected 3, found 4"
    )

    conflict_metrics = metrics_registry.get_combat_conflict_metrics()
    assert conflict_metrics["total_concurrency_conflicts"] == 1
    assert conflict_metrics["recent_conflicts"][0]["session_id"] == "sess-123"
    assert "OptimisticLockVersionMismatch" in conflict_metrics["recent_conflicts"][0]["reason"]


def test_admin_system_metrics_endpoint(admin_client):
    """Verify GET /api/v1/admin/system/metrics returns all 9 observability dimensions."""
    res = admin_client.get("/api/v1/admin/system/metrics")
    assert res.status_code == 200
    data = res.json()

    # Verify all 9 dimensions
    assert "database_query_latency" in data
    assert "connection_pool" in data
    assert "bundle_load_time_ms" in data
    assert "cache_hits_misses" in data
    assert "cache_memory_consumption" in data
    assert "json_fallback" in data
    assert "ingestion_validation" in data
    assert "content_version_mismatches" in data
    assert "combat_concurrency_conflicts" in data


def test_admin_system_config_includes_metrics(admin_client):
    """Verify GET /api/v1/admin/system/config includes system metrics."""
    res = admin_client.get("/api/v1/admin/system/config")
    assert res.status_code == 200
    data = res.json()
    assert "metrics" in data
    assert "database_query_latency" in data["metrics"]
    assert "connection_pool" in data["metrics"]
    assert "cache_hits_misses" in data["metrics"]
