"""FastAPI routes for Legacy Code Analyzer."""
import asyncio
import hashlib
from typing import Annotated, List, Optional
import uuid

import structlog
from fastapi import (
    APIRouter,
    BackgroundTasks,
    Depends,
    File,
    Form,
    HTTPException,
    Query,
    Response,
    UploadFile,
    status,
)
from sqlalchemy import desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.analyzer.pipeline import PipelineRunner, unpack_zip_safely
from app.analyzer.serializers import (
    export_as_csv,
    export_as_dot,
    export_as_json,
    export_as_markdown,
    export_as_mermaid,
)
from app.core.config import settings
from app.core.database import get_db_session
from app.core.security import CurrentUserId
from app.models.models import (
    AnalysisRun,
    BlockAnalysis,
    CodeBlock,
    Condition,
    Finding,
    GraphEdge,
    GraphNode,
    PhaseRun,
    SourceFile,
    UsageRecord,
)
from app.schemas.schemas import (
    AnalysisCreateRequest,
    AnalysisDetailResponse,
    AnalysisListResponse,
    AnalysisRunResponse,
    BlockDetailResponse,
    CodeBlockResponse,
    ConditionResponse,
    FindingResponse,
    GraphEdgeResponse,
    GraphNodeResponse,
    GraphResponse,
    LineageResponse,
    LineageStep,
    MessageResponse,
    PhaseRunResponse,
    TranslationContextResponse,
)

router = APIRouter()
logger = structlog.get_logger()

ANALYSIS_MONTHLY_LIMIT = 20
MAX_UPLOAD_BYTES = 2 * 1024 * 1024  # 2 MB
MAX_FILES = 50


async def check_and_increment_analysis_quota(db: AsyncSession, user_id: uuid.UUID) -> None:
    """Enforce per-user monthly analysis quota."""
    from datetime import datetime, timezone
    now = datetime.now(timezone.utc)
    month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)

    stmt = select(UsageRecord).where(
        UsageRecord.user_id == user_id,
        UsageRecord.month == month_start,
    )
    res = await db.execute(stmt)
    usage = res.scalar_one_or_none()

    current_count = usage.analysis_count if usage else 0
    if current_count >= ANALYSIS_MONTHLY_LIMIT:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail={
                "code": "QUOTA_EXCEEDED",
                "message": f"Monthly analysis quota of {ANALYSIS_MONTHLY_LIMIT} runs reached.",
            },
        )

    if not usage:
        usage = UsageRecord(user_id=user_id, month=month_start, analysis_count=1)
        db.add(usage)
    else:
        usage.analysis_count += 1
    await db.flush()


@router.post("", response_model=AnalysisRunResponse, status_code=status.HTTP_202_ACCEPTED)
async def create_analysis(
    user_id: CurrentUserId,
    db: Annotated[AsyncSession, Depends(get_db_session)],
    background_tasks: BackgroundTasks,
    language: str = Form(default="cobol"),
    files: Optional[List[UploadFile]] = File(default=None),
) -> AnalysisRunResponse:
    """Create and enqueue a new legacy code analysis run (multipart/form-data)."""
    user_uuid = uuid.UUID(user_id)
    await check_and_increment_analysis_quota(db, user_uuid)

    extracted_files: List[tuple[str, str, str]] = []  # path, content, role
    total_bytes = 0

    if files:
        for uploaded in files:
            content_bytes = await uploaded.read()
            total_bytes += len(content_bytes)
            if total_bytes > MAX_UPLOAD_BYTES:
                raise HTTPException(
                    status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                    detail={"code": "FILE_TOO_LARGE", "message": "Uploaded content exceeds 2 MB limit."},
                )

            filename = uploaded.filename or "unknown.cbl"
            if filename.lower().endswith(".zip"):
                try:
                    unpacked = unpack_zip_safely(content_bytes, max_files=MAX_FILES, max_total_bytes=MAX_UPLOAD_BYTES)
                    for uf in unpacked:
                        extracted_files.append((uf.path, uf.content, uf.role))
                except ValueError as ve:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail={"code": "INVALID_ARCHIVE", "message": str(ve)},
                    )
            else:
                text = content_bytes.decode("utf-8", errors="replace")
                role = "copybook" if filename.upper().endswith((".CPY", ".COPY")) else "main"
                extracted_files.append((filename, text, role))

    if not extracted_files:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"code": "NO_FILES", "message": "Please provide at least one source file or archive."},
        )

    # Create run record
    run = AnalysisRun(
        user_id=user_uuid,
        language=language,
        status="pending",
        current_phase="phase_0",
    )
    db.add(run)
    await db.flush()

    for path, content, role in extracted_files:
        sha256 = hashlib.sha256(content.encode("utf-8")).hexdigest()
        sf = SourceFile(
            run_id=run.id,
            path=path,
            role=role,
            sha256=sha256,
            content=content,
        )
        db.add(sf)

    await db.commit()
    await db.refresh(run)

    # Launch pipeline in background
    runner = PipelineRunner(run.id)
    background_tasks.add_task(runner.execute)

    return run


@router.get("", response_model=AnalysisListResponse)
async def list_analyses(
    user_id: CurrentUserId,
    db: Annotated[AsyncSession, Depends(get_db_session)],
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
) -> AnalysisListResponse:
    """List paginated analysis runs for the authenticated user."""
    user_uuid = uuid.UUID(user_id)
    count_stmt = select(func.count(AnalysisRun.id)).where(AnalysisRun.user_id == user_uuid)
    total = (await db.execute(count_stmt)).scalar() or 0

    stmt = (
        select(AnalysisRun)
        .where(AnalysisRun.user_id == user_uuid)
        .order_by(desc(AnalysisRun.created_at))
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    res = await db.execute(stmt)
    runs = res.scalars().all()

    return AnalysisListResponse(
        items=list(runs),
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get("/{id}", response_model=AnalysisDetailResponse)
async def get_analysis(
    id: uuid.UUID,
    user_id: CurrentUserId,
    db: Annotated[AsyncSession, Depends(get_db_session)],
) -> AnalysisDetailResponse:
    """Get single analysis run status, timing, and phase progress."""
    user_uuid = uuid.UUID(user_id)
    stmt = (
        select(AnalysisRun)
        .options(selectinload(AnalysisRun.phase_runs))
        .where(AnalysisRun.id == id, AnalysisRun.user_id == user_uuid)
    )
    res = await db.execute(stmt)
    run = res.scalar_one_or_none()
    if not run:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "NOT_FOUND", "message": "Analysis run not found."},
        )

    return AnalysisDetailResponse(
        id=run.id,
        user_id=run.user_id,
        status=run.status,
        current_phase=run.current_phase,
        language=run.language,
        created_at=run.created_at,
        completed_at=run.completed_at,
        token_totals=run.token_totals,
        error=run.error,
        phases=[PhaseRunResponse.model_validate(p) for p in run.phase_runs],
    )


@router.post("/{id}/retry", response_model=AnalysisRunResponse)
async def retry_analysis(
    id: uuid.UUID,
    user_id: CurrentUserId,
    db: Annotated[AsyncSession, Depends(get_db_session)],
    background_tasks: BackgroundTasks,
) -> AnalysisRunResponse:
    """Resume a failed or interrupted analysis run from its last checkpoint."""
    user_uuid = uuid.UUID(user_id)
    run = await db.get(AnalysisRun, id)
    if not run or run.user_id != user_uuid:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "NOT_FOUND", "message": "Analysis run not found."},
        )

    run.status = "pending"
    run.error = None
    await db.commit()

    runner = PipelineRunner(run.id)
    background_tasks.add_task(runner.execute)

    return run


@router.get("/{id}/blocks", response_model=List[CodeBlockResponse])
async def get_blocks(
    id: uuid.UUID,
    user_id: CurrentUserId,
    db: Annotated[AsyncSession, Depends(get_db_session)],
) -> List[CodeBlockResponse]:
    """List code blocks for an analysis run."""
    user_uuid = uuid.UUID(user_id)
    stmt = (
        select(CodeBlock)
        .join(AnalysisRun)
        .where(CodeBlock.run_id == id, AnalysisRun.user_id == user_uuid)
        .order_by(CodeBlock.start_line)
    )
    res = await db.execute(stmt)
    return list(res.scalars().all())


@router.get("/{id}/blocks/{block_id}", response_model=BlockDetailResponse)
async def get_block_detail(
    id: uuid.UUID,
    block_id: uuid.UUID,
    user_id: CurrentUserId,
    db: Annotated[AsyncSession, Depends(get_db_session)],
) -> BlockDetailResponse:
    """Get single block with conditions and verified reasoning."""
    user_uuid = uuid.UUID(user_id)
    stmt = (
        select(CodeBlock)
        .options(selectinload(CodeBlock.conditions), selectinload(CodeBlock.analysis))
        .join(AnalysisRun)
        .where(CodeBlock.id == block_id, CodeBlock.run_id == id, AnalysisRun.user_id == user_uuid)
    )
    res = await db.execute(stmt)
    block = res.scalar_one_or_none()
    if not block:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "NOT_FOUND", "message": "Code block not found."},
        )

    # Load source file to slice lines
    sf_stmt = select(SourceFile).where(SourceFile.run_id == id, SourceFile.role == "main")
    sf = (await db.execute(sf_stmt)).scalars().first()
    source_slice = ""
    if sf:
        lines = sf.content.splitlines()
        slice_lines = lines[max(0, block.start_line - 1):block.end_line]
        source_slice = "\n".join(slice_lines)

    return BlockDetailResponse(
        block=CodeBlockResponse.model_validate(block),
        source_slice=source_slice,
        conditions=[ConditionResponse.model_validate(c) for c in block.conditions],
        analysis=block.analysis,
    )


@router.get("/{id}/graph", response_model=GraphResponse)
async def get_graph(
    id: uuid.UUID,
    user_id: CurrentUserId,
    db: Annotated[AsyncSession, Depends(get_db_session)],
    edge_type: Optional[str] = Query(default=None),
) -> GraphResponse:
    """Get graph nodes and edges for dependency map visualization."""
    user_uuid = uuid.UUID(user_id)
    run_check = await db.execute(
        select(AnalysisRun.id).where(AnalysisRun.id == id, AnalysisRun.user_id == user_uuid)
    )
    if not run_check.scalar_one_or_none():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail={"code": "NOT_FOUND", "message": "Run not found."})

    nodes_stmt = select(GraphNode).where(GraphNode.run_id == id)
    nodes = (await db.execute(nodes_stmt)).scalars().all()

    edges_stmt = select(GraphEdge).where(GraphEdge.run_id == id)
    if edge_type:
        edges_stmt = edges_stmt.where(GraphEdge.edge_type == edge_type.upper())
    edges = (await db.execute(edges_stmt)).scalars().all()

    return GraphResponse(
        nodes=[GraphNodeResponse.model_validate(n) for n in nodes],
        edges=[GraphEdgeResponse.model_validate(e) for e in edges],
    )


@router.get("/{id}/conditions", response_model=List[ConditionResponse])
async def get_conditions(
    id: uuid.UUID,
    user_id: CurrentUserId,
    db: Annotated[AsyncSession, Depends(get_db_session)],
    block_id: Optional[uuid.UUID] = Query(default=None),
    kind: Optional[str] = Query(default=None),
) -> List[ConditionResponse]:
    """List extracted control flow and business conditions."""
    user_uuid = uuid.UUID(user_id)
    stmt = (
        select(Condition)
        .join(CodeBlock)
        .join(AnalysisRun)
        .where(CodeBlock.run_id == id, AnalysisRun.user_id == user_uuid)
    )
    if block_id:
        stmt = stmt.where(Condition.block_id == block_id)
    if kind:
        stmt = stmt.where(Condition.kind == kind.upper())

    stmt = stmt.order_by(Condition.start_line)
    res = await db.execute(stmt)
    return list(res.scalars().all())


@router.get("/{id}/lineage", response_model=LineageResponse)
async def get_lineage(
    id: uuid.UUID,
    item: str,
    user_id: CurrentUserId,
    db: Annotated[AsyncSession, Depends(get_db_session)],
) -> LineageResponse:
    """Trace data item usage across all code blocks."""
    user_uuid = uuid.UUID(user_id)
    # Find data item node
    item_node_stmt = select(GraphNode).where(GraphNode.run_id == id, GraphNode.name == item.upper())
    item_node = (await db.execute(item_node_stmt)).scalar_one_or_none()

    edges_stmt = (
        select(GraphEdge, GraphNode)
        .join(GraphNode, GraphEdge.source_node_id == GraphNode.id)
        .where(
            GraphEdge.run_id == id,
            GraphEdge.target_node_id == (item_node.id if item_node else uuid.uuid4()),
        )
        .order_by(GraphEdge.source_line)
    )
    res = await db.execute(edges_stmt)
    rows = res.all()

    steps: List[LineageStep] = []
    for order, (edge, src_node) in enumerate(rows, 1):
        if src_node.ref_id:
            steps.append(
                LineageStep(
                    block_id=src_node.ref_id,
                    block_name=src_node.name,
                    access_type=edge.edge_type,
                    source_line=edge.source_line,
                    order=order,
                )
            )

    return LineageResponse(
        item_name=item.upper(),
        definition=item_node.metadata_json if item_node else None,
        references=steps,
    )


@router.get("/{id}/findings", response_model=List[FindingResponse])
async def get_findings(
    id: uuid.UUID,
    user_id: CurrentUserId,
    db: Annotated[AsyncSession, Depends(get_db_session)],
    severity: Optional[str] = Query(default=None),
) -> List[FindingResponse]:
    """List static & semantic diagnostic findings."""
    user_uuid = uuid.UUID(user_id)
    stmt = (
        select(Finding)
        .join(AnalysisRun)
        .where(Finding.run_id == id, AnalysisRun.user_id == user_uuid)
    )
    if severity:
        stmt = stmt.where(Finding.severity == severity.lower())
    res = await db.execute(stmt)
    return list(res.scalars().all())


@router.get("/{id}/export")
async def export_analysis(
    id: uuid.UUID,
    user_id: CurrentUserId,
    db: Annotated[AsyncSession, Depends(get_db_session)],
    format: str = Query(default="json", regex="^(json|md|mermaid|dot|csv)$"),
) -> Response:
    """Export analysis as JSON, Markdown, Mermaid, Graphviz DOT, or CSV."""
    user_uuid = uuid.UUID(user_id)
    run = await db.get(AnalysisRun, id)
    if not run or run.user_id != user_uuid:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail={"code": "NOT_FOUND", "message": "Run not found."})

    blocks = (await db.execute(select(CodeBlock).where(CodeBlock.run_id == id))).scalars().all()
    conds = (await db.execute(select(Condition).join(CodeBlock).where(CodeBlock.run_id == id))).scalars().all()
    nodes = (await db.execute(select(GraphNode).where(GraphNode.run_id == id))).scalars().all()
    edges = (await db.execute(select(GraphEdge).where(GraphEdge.run_id == id))).scalars().all()
    findings = (await db.execute(select(Finding).where(Finding.run_id == id))).scalars().all()

    b_dicts = [b.__dict__ for b in blocks]
    c_dicts = [c.__dict__ for c in conds]
    n_dicts = [n.__dict__ for n in nodes]
    e_dicts = [e.__dict__ for e in edges]
    f_dicts = [f.__dict__ for f in findings]

    if format == "json":
        data = export_as_json(run.__dict__, b_dicts, c_dicts, n_dicts, e_dicts, f_dicts)
        return Response(content=data, media_type="application/json")
    elif format == "md":
        data = export_as_markdown(run.__dict__, b_dicts, c_dicts, f_dicts)
        return Response(content=data, media_type="text/markdown")
    elif format == "mermaid":
        data = export_as_mermaid(n_dicts, e_dicts)
        return Response(content=data, media_type="text/plain")
    elif format == "dot":
        data = export_as_dot(n_dicts, e_dicts)
        return Response(content=data, media_type="text/vnd.graphviz")
    elif format == "csv":
        data = export_as_csv(c_dicts)
        return Response(content=data, media_type="text/csv")

    raise HTTPException(status_code=400, detail="Invalid format.")


@router.get("/{id}/translation-context", response_model=TranslationContextResponse)
async def get_translation_context(
    id: uuid.UUID,
    block_id: uuid.UUID,
    user_id: CurrentUserId,
    db: Annotated[AsyncSession, Depends(get_db_session)],
) -> TranslationContextResponse:
    """Return verified block context packet for future block-wise code synthesis."""
    user_uuid = uuid.UUID(user_id)
    block_stmt = (
        select(CodeBlock)
        .options(selectinload(CodeBlock.conditions), selectinload(CodeBlock.analysis))
        .join(AnalysisRun)
        .where(CodeBlock.id == block_id, CodeBlock.run_id == id, AnalysisRun.user_id == user_uuid)
    )
    block = (await db.execute(block_stmt)).scalar_one_or_none()
    if not block:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail={"code": "NOT_FOUND", "message": "Block not found."})

    # Load source file to slice lines
    sf_stmt = select(SourceFile).where(SourceFile.run_id == id, SourceFile.role == "main")
    sf = (await db.execute(sf_stmt)).scalars().first()
    source_slice = ""
    if sf:
        lines = sf.content.splitlines()
        slice_lines = lines[max(0, block.start_line - 1):block.end_line]
        source_slice = "\n".join(slice_lines)

    path_conds = [c.normalized_predicate for c in block.conditions if c.reachable_when]

    return TranslationContextResponse(
        block_id=block.id,
        block_name=block.name,
        source_code=source_slice,
        data_dictionary=[],
        callee_summaries=[],
        path_conditions=path_conds,
    )


@router.delete("/{id}", response_model=MessageResponse)
async def delete_analysis(
    id: uuid.UUID,
    user_id: CurrentUserId,
    db: Annotated[AsyncSession, Depends(get_db_session)],
) -> MessageResponse:
    """Delete analysis run and all associated artifacts."""
    user_uuid = uuid.UUID(user_id)
    run = await db.get(AnalysisRun, id)
    if not run or run.user_id != user_uuid:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail={"code": "NOT_FOUND", "message": "Run not found."})

    await db.delete(run)
    await db.commit()
    return MessageResponse(message="Analysis run deleted successfully.")
