"""Integration tests for Legacy Code Analyzer API endpoints."""
import io
from pathlib import Path
import uuid
import zipfile

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.analyzer.llm.client import MockLLMClient
from app.analyzer.pipeline import PipelineRunner
from app.models.models import AnalysisRun, UsageRecord
from tests.conftest import TEST_USER_ID

FIXTURES_DIR = Path(__file__).parent / "fixtures" / "cobol"


def _read_fixture(filename: str) -> str:
    with open(FIXTURES_DIR / filename, "r", encoding="utf-8") as f:
        return f.read()


@pytest.mark.asyncio
async def test_create_analysis_validation(client: AsyncClient, auth_headers: dict[str, str]):
    """Test validation errors for analysis creation."""
    # 1. No files
    resp = await client.post("/api/v1/analyses", headers=auth_headers, data={"language": "cobol"})
    assert resp.status_code == 400
    assert resp.json()["detail"]["code"] == "NO_FILES"

    # 2. File too large
    big_content = b"X" * (2 * 1024 * 1024 + 10)
    files = [("files", ("large.cbl", big_content, "text/plain"))]
    resp = await client.post("/api/v1/analyses", headers=auth_headers, files=files, data={"language": "cobol"})
    assert resp.status_code == 413
    assert resp.json()["detail"]["code"] == "FILE_TOO_LARGE"

    # 3. Unauthenticated
    resp = await client.post("/api/v1/analyses", data={"language": "cobol"})
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_analysis_quota_limit(client: AsyncClient, auth_headers: dict[str, str], db_session: AsyncSession):
    """Test 429 when user exceeds monthly analysis quota."""
    from datetime import datetime, timezone
    now = datetime.now(timezone.utc)
    month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)

    # Seed quota at limit
    record = UsageRecord(
        user_id=uuid.UUID(TEST_USER_ID),
        month=month_start,
        analysis_count=20,
    )
    db_session.add(record)
    await db_session.commit()

    files = [("files", ("test.cbl", b"IDENTIFICATION DIVISION.", "text/plain"))]
    resp = await client.post("/api/v1/analyses", headers=auth_headers, files=files, data={"language": "cobol"})
    assert resp.status_code == 429
    assert resp.json()["detail"]["code"] == "QUOTA_EXCEEDED"


@pytest.mark.asyncio
async def test_full_analysis_workflow_and_endpoints(
    client: AsyncClient,
    auth_headers: dict[str, str],
    db_session: AsyncSession,
):
    """Test end-to-end pipeline run with MockLLM and verify all API endpoints."""
    payroll_code = _read_fixture("PAYROLL.cbl")
    emprec_code = _read_fixture("EMPREC.cpy")

    # Create a zip containing PAYROLL.cbl and EMPREC.cpy
    zip_buffer = io.BytesIO()
    with zipfile.ZipFile(zip_buffer, "w") as zf:
        zf.writestr("PAYROLL.cbl", payroll_code)
        zf.writestr("EMPREC.cpy", emprec_code)
    zip_bytes = zip_buffer.getvalue()

    # 1. POST /api/v1/analyses with zip
    files = [("files", ("project.zip", zip_bytes, "application/zip"))]
    resp = await client.post("/api/v1/analyses", headers=auth_headers, files=files, data={"language": "cobol"})
    assert resp.status_code == 202
    data = resp.json()
    run_id = data["id"]
    assert data["status"] in ("pending", "running")
    assert data["language"] == "cobol"

    # 2. Run pipeline synchronously using MockLLMClient
    runner = PipelineRunner(uuid.UUID(run_id), llm_client=MockLLMClient())
    await runner.execute()

    # 3. GET /api/v1/analyses (list)
    resp = await client.get("/api/v1/analyses", headers=auth_headers)
    assert resp.status_code == 200
    list_data = resp.json()
    assert list_data["total"] >= 1
    found_run = next(r for r in list_data["items"] if r["id"] == run_id)
    assert found_run["status"] == "completed"

    # 4. GET /api/v1/analyses/{id} (detail)
    resp = await client.get(f"/api/v1/analyses/{run_id}", headers=auth_headers)
    assert resp.status_code == 200
    detail = resp.json()
    assert detail["status"] == "completed"
    assert len(detail["phases"]) == 7
    assert all(p["status"] == "completed" for p in detail["phases"])
    assert detail["source_files_count"] == 2
    assert detail["blocks_count"] > 0
    assert detail["conditions_count"] > 0
    assert detail["graph_nodes_count"] > 0
    assert detail["graph_edges_count"] > 0

    # 5. GET /api/v1/analyses/{id}/blocks
    resp = await client.get(f"/api/v1/analyses/{run_id}/blocks", headers=auth_headers)
    assert resp.status_code == 200
    blocks = resp.json()
    assert len(blocks) > 0
    block_id = blocks[0]["id"]

    # 6. GET /api/v1/analyses/{id}/blocks/{block_id}
    resp = await client.get(f"/api/v1/analyses/{run_id}/blocks/{block_id}", headers=auth_headers)
    assert resp.status_code == 200
    block_detail = resp.json()
    assert block_detail["id"] == block_id
    assert block_detail["analysis"] is not None
    assert "business_rules" in block_detail["analysis"]

    # 7. GET /api/v1/analyses/{id}/graph
    resp = await client.get(f"/api/v1/analyses/{run_id}/graph", headers=auth_headers)
    assert resp.status_code == 200
    graph = resp.json()
    assert len(graph["nodes"]) > 0
    assert len(graph["edges"]) > 0

    # 8. GET /api/v1/analyses/{id}/conditions
    resp = await client.get(f"/api/v1/analyses/{run_id}/conditions", headers=auth_headers)
    assert resp.status_code == 200
    conditions = resp.json()
    assert len(conditions) > 0

    # 9. GET /api/v1/analyses/{id}/lineage?target=EMP-SALARY
    resp = await client.get(f"/api/v1/analyses/{run_id}/lineage?target=EMP-SALARY", headers=auth_headers)
    assert resp.status_code == 200
    lineage = resp.json()
    assert lineage["target_variable"] == "EMP-SALARY"
    assert len(lineage["steps"]) > 0

    # 10. GET /api/v1/analyses/{id}/findings
    resp = await client.get(f"/api/v1/analyses/{run_id}/findings", headers=auth_headers)
    assert resp.status_code == 200
    findings = resp.json()
    assert isinstance(findings, list)

    # 11. GET /api/v1/analyses/{id}/export formats
    for fmt in ("json", "mermaid", "dot", "md", "csv"):
        resp = await client.get(f"/api/v1/analyses/{run_id}/export?format={fmt}", headers=auth_headers)
        assert resp.status_code == 200, f"Export format {fmt} failed with {resp.status_code}"
        assert len(resp.text) > 0

    # 12. GET /api/v1/analyses/{id}/translation-context
    resp = await client.get(f"/api/v1/analyses/{run_id}/translation-context?block_id={block_id}", headers=auth_headers)
    assert resp.status_code == 200
    tc = resp.json()
    assert tc["block_id"] == block_id
    assert tc["source_code"] is not None
    assert len(tc["inbound_callers"]) >= 0

    # 13. DELETE /api/v1/analyses/{id}
    resp = await client.delete(f"/api/v1/analyses/{run_id}", headers=auth_headers)
    assert resp.status_code == 200

    # 14. Verify deletion
    resp = await client.get(f"/api/v1/analyses/{run_id}", headers=auth_headers)
    assert resp.status_code == 404
