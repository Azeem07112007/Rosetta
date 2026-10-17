"""Orchestrator and state machine executing analysis phases with database checkpoints."""
import hashlib
import io
import json
import zipfile
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple
import uuid

import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.analyzer.adapters.base import (
    Block,
    ExtractedCondition,
    FindingItem,
    GraphEdgeItem,
    LanguageAdapter,
    NormalizedFile,
    RawFile,
    StructureResult,
)
from app.analyzer.adapters.cobol.adapter import CobolAdapter
from app.analyzer.graph import AssembledGraph, assemble_graph
from app.analyzer.llm.client import GeminiLLMClient, LLMClient
from app.analyzer.reasoning import analyze_blocks_leaf_first, compute_complexity_and_risk
from app.core.database import async_session_maker
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
)

logger = structlog.get_logger()


def unpack_zip_safely(
    zip_bytes: bytes,
    max_files: int = 50,
    max_total_bytes: int = 2 * 1024 * 1024,
) -> List[RawFile]:
    """Safely extract uploaded zip archive, preventing zip-slip path traversal and zip bombs."""
    raw_files: List[RawFile] = []
    total_bytes = 0

    with zipfile.ZipFile(io.BytesIO(zip_bytes)) as zf:
        infolist = zf.infolist()
        if len(infolist) > max_files:
            raise ValueError(f"Zip archive contains {len(infolist)} files (maximum allowed: {max_files}).")

        for info in infolist:
            if info.is_dir():
                continue
            # Path traversal prevention
            filename = info.filename.replace("\\", "/")
            if filename.startswith("/") or ".." in filename.split("/"):
                raise ValueError(f"Suspicious path in archive: '{filename}'")

            total_bytes += info.file_size
            if total_bytes > max_total_bytes:
                raise ValueError(f"Total uncompressed size exceeds {max_total_bytes // (1024 * 1024)} MB limit.")

            with zf.open(info) as f:
                content = f.read().decode("utf-8", errors="replace")

            role = "copybook" if filename.upper().endswith((".CPY", ".COPY")) else "main"
            raw_files.append(RawFile(path=filename, content=content, role=role))

    return raw_files


class PipelineRunner:
    """State machine that executes analyzer pipeline phases with transactional checkpoints."""

    def __init__(
        self,
        run_id: uuid.UUID,
        adapter: Optional[LanguageAdapter] = None,
        llm_client: Optional[LLMClient] = None,
    ) -> None:
        self.run_id = run_id
        self.adapter = adapter or CobolAdapter()
        self.llm_client = llm_client or GeminiLLMClient()

    async def _get_or_create_phase_run(self, db: AsyncSession, phase_name: str) -> PhaseRun:
        stmt = select(PhaseRun).where(PhaseRun.run_id == self.run_id, PhaseRun.phase == phase_name)
        result = await db.execute(stmt)
        pr = result.scalar_one_or_none()
        if not pr:
            pr = PhaseRun(
                run_id=self.run_id,
                phase=phase_name,
                status="running",
                started_at=datetime.now(timezone.utc),
            )
            db.add(pr)
            await db.flush()
        else:
            pr.status = "running"
            pr.started_at = datetime.now(timezone.utc)
            await db.flush()
        return pr

    async def execute(self) -> None:
        """Run all phases from current state until completion or failure."""
        async with async_session_maker() as db:
            run = await db.get(AnalysisRun, self.run_id)
            if not run:
                logger.error("analyzer_run_not_found", run_id=str(self.run_id))
                return

            run.status = "running"
            await db.commit()

            # Load source files from DB
            sf_stmt = select(SourceFile).where(SourceFile.run_id == self.run_id)
            sf_res = await db.execute(sf_stmt)
            source_files = sf_res.scalars().all()
            raw_files = [RawFile(path=sf.path, content=sf.content, role=sf.role) for sf in source_files]

        try:
            # Phase 0: Normalization & Copybook resolution
            async with async_session_maker() as db:
                pr0 = await self._get_or_create_phase_run(db, "phase_0")
                norm_files, norm_findings = self.adapter.normalize(raw_files)
                pr0.status = "completed"
                pr0.finished_at = datetime.now(timezone.utc)
                await db.commit()

            # Phase 1: Structural Parse
            async with async_session_maker() as db:
                pr1 = await self._get_or_create_phase_run(db, "phase_1")
                structure = self.adapter.parse_structure(norm_files)
                pr1.status = "completed"
                pr1.finished_at = datetime.now(timezone.utc)
                await db.commit()

            # Phase 2: Segmentation
            async with async_session_maker() as db:
                pr2 = await self._get_or_create_phase_run(db, "phase_2")
                blocks = self.adapter.segment_blocks(structure, norm_files)
                pr2.status = "completed"
                pr2.finished_at = datetime.now(timezone.utc)
                await db.commit()

            # Phase 3: CFG, Data Flow & Conditions
            async with async_session_maker() as db:
                pr3 = await self._get_or_create_phase_run(db, "phase_3")
                edges, conditions, phase3_findings = self.adapter.extract_edges_and_conditions(
                    blocks, structure, norm_files
                )
                pr3.status = "completed"
                pr3.finished_at = datetime.now(timezone.utc)
                await db.commit()

            # Phase 4: Graph Assembly & Cycle Detection
            async with async_session_maker() as db:
                pr4 = await self._get_or_create_phase_run(db, "phase_4")
                graph = assemble_graph(blocks, edges, structure)
                pr4.status = "completed"
                pr4.finished_at = datetime.now(timezone.utc)
                await db.commit()

            # Phase 5: Block Reasoning (LLM)
            async with async_session_maker() as db:
                pr5 = await self._get_or_create_phase_run(db, "phase_5")
                block_analyses, tokens_used, phase5_findings = await analyze_blocks_leaf_first(
                    blocks, structure, edges, conditions, graph, self.llm_client
                )
                pr5.status = "completed"
                pr5.finished_at = datetime.now(timezone.utc)
                pr5.tokens = {"total": tokens_used}
                await db.commit()

            # Phase 6 & 7: Complexity Scoring, Findings & Persistence
            async with async_session_maker() as db:
                pr6 = await self._get_or_create_phase_run(db, "phase_6")

                # Compute complexity per block
                block_complexities: Dict[str, Dict[str, Any]] = {}
                for b in blocks:
                    block_complexities[b.name] = compute_complexity_and_risk(
                        b, conditions, edges, graph, all_blocks=blocks
                    )

                # Persist CodeBlocks
                db_blocks: Dict[str, CodeBlock] = {}
                for b in blocks:
                    cb = CodeBlock(
                        run_id=self.run_id,
                        name=b.name,
                        kind=b.kind,
                        start_line=b.start_line,
                        end_line=b.end_line,
                        parse_status=b.parse_status,
                        raw_hash=b.raw_hash,
                        complexity=block_complexities.get(b.name, {}),
                    )
                    db.add(cb)
                    db_blocks[b.name] = cb
                await db.flush()

                # Persist Conditions
                for c in conditions:
                    cb = db_blocks.get(c.block_name or "")
                    if cb:
                        cond = Condition(
                            block_id=cb.id,
                            kind=c.kind,
                            start_line=c.start_line,
                            end_line=c.end_line,
                            raw_expression=c.raw_expression,
                            normalized_predicate=c.normalized_predicate,
                            operands=c.operands,
                            branches=[b.__dict__ if hasattr(b, "__dict__") else b for b in c.branches],
                            nesting_depth=c.nesting_depth,
                            reachable_when=c.reachable_when,
                            plain_english=c.plain_english,
                        )
                        db.add(cond)
                await db.flush()

                # Persist Block Analyses
                for b_name, analysis_dict in block_analyses.items():
                    cb = db_blocks.get(b_name)
                    if cb:
                        ba = BlockAnalysis(
                            block_id=cb.id,
                            schema_version=1,
                            result=analysis_dict,
                            validation={"unverified_count": len(analysis_dict.get("unverified_claims", []))},
                            model_used=settings.GEMINI_MODEL,
                            tokens=tokens_used,
                        )
                        db.add(ba)
                await db.flush()

                # Persist Graph Nodes & Edges
                db_nodes: Dict[str, GraphNode] = {}
                for name, n_data in graph.nodes.items():
                    gn = GraphNode(
                        run_id=self.run_id,
                        node_type=n_data.node_type,
                        name=name,
                        ref_id=db_blocks[name].id if name in db_blocks else None,
                        metadata_json=n_data.metadata,
                    )
                    db.add(gn)
                    db_nodes[name] = gn
                await db.flush()

                for e in edges:
                    src_node = db_nodes.get(e.source_name)
                    tgt_node = db_nodes.get(e.target_name)
                    if src_node and tgt_node:
                        ge = GraphEdge(
                            run_id=self.run_id,
                            source_node_id=src_node.id,
                            target_node_id=tgt_node.id,
                            edge_type=e.edge_type,
                            source_line=e.source_line,
                            is_conditional=e.is_conditional,
                            metadata_json=e.metadata,
                        )
                        db.add(ge)
                await db.flush()

                # Collect and persist all findings
                all_findings = norm_findings + phase3_findings + graph.findings + phase5_findings
                for f in all_findings:
                    cb = db_blocks.get(f.block_name or "") if f.block_name else None
                    db_f = Finding(
                        run_id=self.run_id,
                        severity=f.severity,
                        kind=f.kind,
                        block_id=cb.id if cb else None,
                        message=f.message,
                        line_ranges=f.line_ranges,
                    )
                    db.add(db_f)

                pr6.status = "completed"
                pr6.finished_at = datetime.now(timezone.utc)

                # Finalize Analysis Run
                run = await db.get(AnalysisRun, self.run_id)
                if run:
                    run.status = "completed"
                    run.completed_at = datetime.now(timezone.utc)
                    run.current_phase = "completed"
                    run.token_totals = {"total": tokens_used}

                await db.commit()
                logger.info("analyzer_pipeline_completed", run_id=str(self.run_id), tokens=tokens_used)

        except Exception as exc:
            logger.error("analyzer_pipeline_failed", run_id=str(self.run_id), error=str(exc))
            async with async_session_maker() as db:
                run = await db.get(AnalysisRun, self.run_id)
                if run:
                    run.status = "failed"
                    run.error = str(exc)
                    await db.commit()
