"""Pydantic schemas for API request/response validation."""
import uuid
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


# --- Error ---

class ErrorDetail(BaseModel):
    code: str
    message: str
    details: dict = Field(default_factory=dict)


class ErrorResponse(BaseModel):
    error: ErrorDetail


# --- Auth ---

class SignUpRequest(BaseModel):
    email: str = Field(..., min_length=5, max_length=255)
    password: str = Field(..., min_length=8, max_length=128)


class SignInRequest(BaseModel):
    email: str = Field(..., min_length=5, max_length=255)
    password: str = Field(..., min_length=1, max_length=128)


class ResetPasswordRequest(BaseModel):
    email: str = Field(..., min_length=5, max_length=255)


class AuthResponse(BaseModel):
    access_token: str
    refresh_token: str
    user_id: str
    email: str


class MessageResponse(BaseModel):
    message: str


# --- Translation ---

class TranslationCreateRequest(BaseModel):
    source_code: str = Field(..., min_length=1, max_length=10000)
    source_language: str = Field(default="auto", max_length=50)
    target_language: str = Field(..., min_length=1, max_length=50)
    explain: bool = Field(default=False)


class TranslationResponse(BaseModel):
    id: uuid.UUID
    source_language: str
    target_language: str
    source_code: str
    translated_code: str
    explanation: Optional[str] = None
    detected_language: Optional[str] = None
    model_used: str
    tokens_used: int
    created_at: datetime

    class Config:
        from_attributes = True


class TranslationListResponse(BaseModel):
    translations: list[TranslationResponse]
    total: int
    page: int
    page_size: int


# --- Usage ---

class UsageResponse(BaseModel):
    translation_count: int
    tokens_consumed: int
    monthly_limit: int
    month: str

    class Config:
        from_attributes = True


# --- Account ---

class AccountResponse(BaseModel):
    id: str
    email: str
    display_name: Optional[str] = None
    created_at: Optional[str] = None


class AccountUpdateRequest(BaseModel):
    display_name: str = Field(..., min_length=1, max_length=100)


# ==============================================================================
# Analyzer Schemas
# ==============================================================================


class FileInput(BaseModel):
    path: str = Field(..., min_length=1, max_length=500)
    content: str = Field(..., min_length=1)


class AnalysisCreateRequest(BaseModel):
    language: str = Field(default="cobol", max_length=50)
    files: list[FileInput] = Field(default_factory=list)


class AnalysisRunResponse(BaseModel):
    id: uuid.UUID
    user_id: uuid.UUID
    status: str
    current_phase: str
    language: str
    created_at: datetime
    completed_at: Optional[datetime] = None
    token_totals: dict = Field(default_factory=dict)
    error: Optional[str] = None

    class Config:
        from_attributes = True


class PhaseRunResponse(BaseModel):
    id: uuid.UUID
    phase: str
    status: str
    started_at: Optional[datetime] = None
    finished_at: Optional[datetime] = None
    tokens: dict = Field(default_factory=dict)
    error: Optional[str] = None

    class Config:
        from_attributes = True


class AnalysisDetailResponse(AnalysisRunResponse):
    phases: list[PhaseRunResponse] = Field(default_factory=list)


class AnalysisListResponse(BaseModel):
    items: list[AnalysisRunResponse]
    total: int
    page: int
    page_size: int


class SourceFileResponse(BaseModel):
    id: uuid.UUID
    run_id: uuid.UUID
    path: str
    role: str
    sha256: str

    class Config:
        from_attributes = True


class CodeBlockResponse(BaseModel):
    id: uuid.UUID
    run_id: uuid.UUID
    file_id: Optional[uuid.UUID] = None
    name: str
    kind: str
    parent_id: Optional[uuid.UUID] = None
    start_line: int
    end_line: int
    parse_status: str
    raw_hash: str
    complexity: dict = Field(default_factory=dict)

    class Config:
        from_attributes = True


class ConditionResponse(BaseModel):
    id: uuid.UUID
    block_id: uuid.UUID
    kind: str
    start_line: int
    end_line: int
    raw_expression: str
    normalized_predicate: str
    operands: list = Field(default_factory=list)
    branches: list = Field(default_factory=list)
    nesting_depth: int
    reachable_when: Optional[str] = None
    plain_english: Optional[str] = None

    class Config:
        from_attributes = True


class BlockAnalysisResponse(BaseModel):
    id: uuid.UUID
    block_id: uuid.UUID
    schema_version: int
    result: dict = Field(default_factory=dict)
    validation: dict = Field(default_factory=dict)
    model_used: str
    tokens: int
    created_at: datetime

    class Config:
        from_attributes = True


class BlockDetailResponse(BaseModel):
    block: CodeBlockResponse
    source_slice: str
    conditions: list[ConditionResponse] = Field(default_factory=list)
    analysis: Optional[BlockAnalysisResponse] = None


class GraphNodeResponse(BaseModel):
    id: uuid.UUID
    run_id: uuid.UUID
    node_type: str
    name: str
    ref_id: Optional[uuid.UUID] = None
    metadata_json: dict = Field(default_factory=dict)

    class Config:
        from_attributes = True


class GraphEdgeResponse(BaseModel):
    id: uuid.UUID
    run_id: uuid.UUID
    source_node_id: uuid.UUID
    target_node_id: uuid.UUID
    edge_type: str
    source_line: Optional[int] = None
    is_conditional: bool
    condition_id: Optional[uuid.UUID] = None
    metadata_json: dict = Field(default_factory=dict)

    class Config:
        from_attributes = True


class GraphResponse(BaseModel):
    nodes: list[GraphNodeResponse]
    edges: list[GraphEdgeResponse]


class FindingResponse(BaseModel):
    id: uuid.UUID
    run_id: uuid.UUID
    severity: str
    kind: str
    block_id: Optional[uuid.UUID] = None
    message: str
    line_ranges: list = Field(default_factory=list)

    class Config:
        from_attributes = True


class LineageStep(BaseModel):
    block_id: uuid.UUID
    block_name: str
    access_type: str  # READS, WRITES, REDEFINES
    source_line: Optional[int] = None
    order: int


class LineageResponse(BaseModel):
    item_name: str
    definition: Optional[dict] = None
    references: list[LineageStep] = Field(default_factory=list)


class TranslationContextResponse(BaseModel):
    block_id: uuid.UUID
    block_name: str
    source_code: str
    data_dictionary: list[dict] = Field(default_factory=list)
    callee_summaries: list[dict] = Field(default_factory=list)
    path_conditions: list[str] = Field(default_factory=list)

