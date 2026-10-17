"""SQLAlchemy models for Rosetta."""
import uuid
from datetime import datetime

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    ForeignKey,
    Integer,
    JSON,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import DeclarativeBase, relationship


class Base(DeclarativeBase):
    """Base class for all SQLAlchemy models."""
    pass


class Translation(Base):
    """A code translation record."""

    __tablename__ = "translations"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    source_language = Column(String(50), nullable=False)
    target_language = Column(String(50), nullable=False)
    source_code = Column(Text, nullable=False)
    translated_code = Column(Text, nullable=False)
    explanation = Column(Text, nullable=True)
    detected_language = Column(String(50), nullable=True)
    model_used = Column(String(100), nullable=False)
    tokens_used = Column(Integer, nullable=False, default=0)
    created_at = Column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )


class UsageRecord(Base):
    """Monthly usage tracking per user."""

    __tablename__ = "usage_records"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    month = Column(DateTime(timezone=True), nullable=False)
    translation_count = Column(Integer, nullable=False, default=0)
    analysis_count = Column(Integer, nullable=False, default=0)
    tokens_consumed = Column(Integer, nullable=False, default=0)

    __table_args__ = (
        UniqueConstraint("user_id", "month", name="uq_user_month"),
    )


# ==============================================================================
# Analyzer Models
# ==============================================================================


class AnalysisRun(Base):
    """A code analysis execution run."""

    __tablename__ = "analysis_runs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    status = Column(String(50), nullable=False, default="pending")  # pending, running, completed, failed
    current_phase = Column(String(50), nullable=False, default="phase_0")
    language = Column(String(50), nullable=False, default="cobol")
    created_at = Column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    completed_at = Column(DateTime(timezone=True), nullable=True)
    token_totals = Column(JSON, nullable=False, default=lambda: {"prompt": 0, "completion": 0, "total": 0})
    error = Column(Text, nullable=True)

    # Relationships
    source_files = relationship("SourceFile", back_populates="run", cascade="all, delete-orphan")
    phase_runs = relationship("PhaseRun", back_populates="run", cascade="all, delete-orphan")
    code_blocks = relationship("CodeBlock", back_populates="run", cascade="all, delete-orphan")
    graph_nodes = relationship("GraphNode", back_populates="run", cascade="all, delete-orphan")
    graph_edges = relationship("GraphEdge", back_populates="run", cascade="all, delete-orphan")
    findings = relationship("Finding", back_populates="run", cascade="all, delete-orphan")


class SourceFile(Base):
    """Uploaded or extracted source code file associated with a run."""

    __tablename__ = "source_files"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    run_id = Column(UUID(as_uuid=True), ForeignKey("analysis_runs.id", ondelete="CASCADE"), nullable=False, index=True)
    path = Column(String(500), nullable=False)
    role = Column(String(50), nullable=False, default="main")  # main, copybook, include
    sha256 = Column(String(64), nullable=False)
    content = Column(Text, nullable=False)

    run = relationship("AnalysisRun", back_populates="source_files")


class PhaseRun(Base):
    """Execution status and metrics for an individual analysis pipeline phase."""

    __tablename__ = "phase_runs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    run_id = Column(UUID(as_uuid=True), ForeignKey("analysis_runs.id", ondelete="CASCADE"), nullable=False, index=True)
    phase = Column(String(50), nullable=False)
    status = Column(String(50), nullable=False, default="pending")  # pending, running, completed, failed, skipped
    started_at = Column(DateTime(timezone=True), nullable=True)
    finished_at = Column(DateTime(timezone=True), nullable=True)
    tokens = Column(JSON, nullable=False, default=lambda: {"prompt": 0, "completion": 0, "total": 0})
    error = Column(Text, nullable=True)

    run = relationship("AnalysisRun", back_populates="phase_runs")


class CodeBlock(Base):
    """A segmented unit of code (section, paragraph, loop, or statement group)."""

    __tablename__ = "code_blocks"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    run_id = Column(UUID(as_uuid=True), ForeignKey("analysis_runs.id", ondelete="CASCADE"), nullable=False, index=True)
    file_id = Column(UUID(as_uuid=True), ForeignKey("source_files.id", ondelete="SET NULL"), nullable=True)
    name = Column(String(200), nullable=False)
    kind = Column(String(50), nullable=False)  # paragraph, section, statement_group, loop
    parent_id = Column(UUID(as_uuid=True), ForeignKey("code_blocks.id", ondelete="SET NULL"), nullable=True)
    start_line = Column(Integer, nullable=False)
    end_line = Column(Integer, nullable=False)
    parse_status = Column(String(50), nullable=False, default="complete")  # complete, partial, failed
    raw_hash = Column(String(64), nullable=False)
    complexity = Column(JSON, nullable=False, default=dict)

    run = relationship("AnalysisRun", back_populates="code_blocks")
    conditions = relationship("Condition", back_populates="block", cascade="all, delete-orphan")
    analysis = relationship("BlockAnalysis", back_populates="block", uselist=False, cascade="all, delete-orphan")


class GraphNode(Base):
    """A node in the architectural / semantic dependency graph."""

    __tablename__ = "graph_nodes"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    run_id = Column(UUID(as_uuid=True), ForeignKey("analysis_runs.id", ondelete="CASCADE"), nullable=False, index=True)
    node_type = Column(String(50), nullable=False)  # program, copybook, block, data_item, file, sql_table, external_program
    name = Column(String(255), nullable=False)
    ref_id = Column(UUID(as_uuid=True), nullable=True)  # References block_id, file_id, etc.
    metadata_json = Column(JSON, nullable=False, default=dict)

    run = relationship("AnalysisRun", back_populates="graph_nodes")


class GraphEdge(Base):
    """A typed dependency or control flow edge between graph nodes."""

    __tablename__ = "graph_edges"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    run_id = Column(UUID(as_uuid=True), ForeignKey("analysis_runs.id", ondelete="CASCADE"), nullable=False, index=True)
    source_node_id = Column(UUID(as_uuid=True), ForeignKey("graph_nodes.id", ondelete="CASCADE"), nullable=False, index=True)
    target_node_id = Column(UUID(as_uuid=True), ForeignKey("graph_nodes.id", ondelete="CASCADE"), nullable=False, index=True)
    edge_type = Column(String(50), nullable=False)  # PERFORMS, PERFORMS_THRU, GOES_TO, GOES_TO_DEPENDING, FALLS_THROUGH, CALLS, CALLS_DYNAMIC, COPIES, READS, WRITES, UPDATES, REDEFINES, ALTERS, FILE_IO, SQL_TABLE
    source_line = Column(Integer, nullable=True)
    is_conditional = Column(Boolean, nullable=False, default=False)
    condition_id = Column(UUID(as_uuid=True), nullable=True)
    metadata_json = Column(JSON, nullable=False, default=dict)

    run = relationship("AnalysisRun", back_populates="graph_edges")


class Condition(Base):
    """A control flow or business decision condition extracted from code."""

    __tablename__ = "conditions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    block_id = Column(UUID(as_uuid=True), ForeignKey("code_blocks.id", ondelete="CASCADE"), nullable=False, index=True)
    kind = Column(String(50), nullable=False)  # IF, EVALUATE_WHEN, PERFORM_UNTIL, PERFORM_VARYING, 88_LEVEL, SEARCH_AT_END, ON_SIZE_ERROR, INVALID_KEY, GO_TO_DEPENDING
    start_line = Column(Integer, nullable=False)
    end_line = Column(Integer, nullable=False)
    raw_expression = Column(Text, nullable=False)
    normalized_predicate = Column(Text, nullable=False)
    operands = Column(JSON, nullable=False, default=list)
    branches = Column(JSON, nullable=False, default=list)  # [{"branch": "then", "target": "2000-PROCESS"}]
    nesting_depth = Column(Integer, nullable=False, default=0)
    reachable_when = Column(Text, nullable=True)
    plain_english = Column(Text, nullable=True)

    block = relationship("CodeBlock", back_populates="conditions")


class BlockAnalysis(Base):
    """LLM reasoning output, classification, and AST verification for a block."""

    __tablename__ = "block_analyses"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    block_id = Column(UUID(as_uuid=True), ForeignKey("code_blocks.id", ondelete="CASCADE"), nullable=False, unique=True, index=True)
    schema_version = Column(Integer, nullable=False, default=1)
    result = Column(JSON, nullable=False, default=dict)
    validation = Column(JSON, nullable=False, default=dict)
    model_used = Column(String(100), nullable=False)
    tokens = Column(Integer, nullable=False, default=0)
    created_at = Column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    block = relationship("CodeBlock", back_populates="analysis")


class Finding(Base):
    """Static and semantic diagnostic findings (risks, unverified claims, anomalies)."""

    __tablename__ = "findings"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    run_id = Column(UUID(as_uuid=True), ForeignKey("analysis_runs.id", ondelete="CASCADE"), nullable=False, index=True)
    severity = Column(String(50), nullable=False)  # critical, warning, info
    kind = Column(String(100), nullable=False)  # DYNAMIC_CALL, ALTER_FOUND, MISSING_COPYBOOK, UNREACHABLE_BLOCK, PARTIAL_PARSE, CONTROL_CYCLE, PACKED_DECIMAL_RISK, UNVERIFIED_LLM_CLAIM
    block_id = Column(UUID(as_uuid=True), ForeignKey("code_blocks.id", ondelete="SET NULL"), nullable=True)
    message = Column(Text, nullable=False)
    line_ranges = Column(JSON, nullable=False, default=list)

    run = relationship("AnalysisRun", back_populates="findings")
