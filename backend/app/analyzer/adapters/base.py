"""Language Adapter interface and abstract base class for code analysis."""
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Set


@dataclass
class RawFile:
    path: str
    content: str
    role: str = "main"  # main, copybook, include


@dataclass
class NormalizedLine:
    original_line_number: int
    text: str
    is_comment: bool = False
    is_continuation: bool = False


@dataclass
class NormalizedFile:
    path: str
    role: str
    sha256: str
    lines: List[NormalizedLine]
    raw_content: str
    normalized_content: str
    format_type: str = "fixed"  # fixed or free


@dataclass
class FindingItem:
    severity: str  # critical, warning, info
    kind: str
    message: str
    line_ranges: List[List[int]] = field(default_factory=list)
    block_name: Optional[str] = None


@dataclass
class DataItem:
    name: str
    level: int
    pic: Optional[str] = None
    usage: Optional[str] = None  # COMP, COMP-3, DISPLAY, etc.
    is_packed_decimal: bool = False
    redefines: Optional[str] = None
    occurs: Optional[int] = None
    condition_88_values: List[str] = field(default_factory=list)
    parent_name: Optional[str] = None
    children: List[str] = field(default_factory=list)
    line_number: int = 0
    is_group: bool = False


@dataclass
class SqlBlock:
    kind: str  # SQL or CICS
    start_line: int
    end_line: int
    raw_statement: str
    target_tables: List[str] = field(default_factory=list)


@dataclass
class StructureResult:
    program_name: str
    divisions: Dict[str, Dict[str, int]]  # division_name -> {"start": line, "end": line}
    sections: List[Dict[str, Any]]
    paragraphs: List[Dict[str, Any]]
    data_items: Dict[str, DataItem] = field(default_factory=dict)
    sql_blocks: List[SqlBlock] = field(default_factory=list)
    files: List[Dict[str, Any]] = field(default_factory=list)  # FDs
    parse_status: str = "complete"  # complete, partial, failed
    findings: List[FindingItem] = field(default_factory=list)


@dataclass
class Block:
    name: str
    kind: str  # paragraph, section, statement_group, loop
    start_line: int
    end_line: int
    file_path: str
    raw_hash: str
    source_text: str
    parent_name: Optional[str] = None
    parse_status: str = "complete"
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ConditionBranch:
    branch: str  # then, else, when_value, other, etc.
    target_name: Optional[str] = None
    lines: List[int] = field(default_factory=list)


@dataclass
class ExtractedCondition:
    kind: str  # IF, EVALUATE_WHEN, PERFORM_UNTIL, PERFORM_VARYING, 88_LEVEL, SEARCH_AT_END, ON_SIZE_ERROR, INVALID_KEY, GO_TO_DEPENDING
    start_line: int
    end_line: int
    raw_expression: str
    normalized_predicate: str
    operands: List[str] = field(default_factory=list)
    branches: List[ConditionBranch] = field(default_factory=list)
    nesting_depth: int = 0
    block_name: Optional[str] = None
    reachable_when: Optional[str] = None
    plain_english: Optional[str] = None


@dataclass
class GraphEdgeItem:
    source_name: str  # block or node name
    target_name: str  # block or node name
    edge_type: str  # PERFORMS, PERFORMS_THRU, GOES_TO, GOES_TO_DEPENDING, FALLS_THROUGH, CALLS, CALLS_DYNAMIC, COPIES, READS, WRITES, UPDATES, REDEFINES, ALTERS, FILE_IO, SQL_TABLE
    source_line: Optional[int] = None
    is_conditional: bool = False
    condition_id: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


class LanguageAdapter(ABC):
    """Abstract interface defining the pipeline contracts for language-specific analysis."""

    @abstractmethod
    def normalize(self, files: List[RawFile]) -> tuple[List[NormalizedFile], List[FindingItem]]:
        """Phase 0: Ingestion and Normalization.
        Detects formatting, handles comments, continuation lines, copybooks, and hashing.
        """
        pass

    @abstractmethod
    def parse_structure(self, normalized_files: List[NormalizedFile]) -> StructureResult:
        """Phase 1: Structural Parsing.
        Extracts divisions, sections, paragraphs, data items, and embedded SQL/CICS.
        """
        pass

    @abstractmethod
    def segment_blocks(self, structure: StructureResult, normalized_files: List[NormalizedFile]) -> List[Block]:
        """Phase 2: Block Segmentation.
        Partitions code into paragraphs/sections or fallback statement groups.
        """
        pass

    @abstractmethod
    def extract_edges_and_conditions(
        self,
        blocks: List[Block],
        structure: StructureResult,
        normalized_files: List[NormalizedFile],
    ) -> tuple[List[GraphEdgeItem], List[ExtractedCondition], List[FindingItem]]:
        """Phase 3: Control flow, data flow, conditions, and typed edges."""
        pass
