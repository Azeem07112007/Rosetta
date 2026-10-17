"""Unit and Acceptance tests for deterministic COBOL parsing and graph assembly."""
import os
import pytest

from app.analyzer.adapters.base import RawFile
from app.analyzer.adapters.cobol.adapter import CobolAdapter
from app.analyzer.graph import assemble_graph

FIXTURES_DIR = os.path.join(os.path.dirname(__file__), "fixtures", "cobol")


def read_fixture(filename: str) -> str:
    with open(os.path.join(FIXTURES_DIR, filename), "r", encoding="utf-8") as f:
        return f.read()


class TestCobolAdapterDeterministic:
    """Tests for Phases 0 through 4 with no LLM dependency."""

    @pytest.fixture
    def adapter(self):
        return CobolAdapter()

    def test_payroll_pipeline(self, adapter):
        """PAYROLL.cbl + EMPREC.cpy acceptance test."""
        payroll_src = read_fixture("PAYROLL.cbl")
        emprec_src = read_fixture("EMPREC.cpy")

        raw_files = [
            RawFile(path="PAYROLL.cbl", content=payroll_src, role="main"),
            RawFile(path="EMPREC.cpy", content=emprec_src, role="copybook"),
        ]

        # Phase 0: Normalization & COPY resolution
        norm_files, norm_findings = adapter.normalize(raw_files)
        assert len(norm_files) == 2
        main_norm = next(f for f in norm_files if f.role == "main")
        assert "EMP-RECORD" in main_norm.normalized_content
        assert "BEGIN COPYBOOK EMPREC" in main_norm.normalized_content

        # Phase 1: Structure Parsing
        structure = adapter.parse_structure(norm_files)
        assert structure.program_name == "PAYROLL"
        assert "PROCEDURE" in structure.divisions
        assert "DATA" in structure.divisions
        # Check resolved copybook items in Data Division
        assert "EMP-RECORD" in structure.data_items
        assert "EMP-ID" in structure.data_items
        assert "EMP-HOURS" in structure.data_items
        assert "FULL-TIME" in structure.data_items
        assert structure.data_items["FULL-TIME"].level == 88

        # Phase 2: Segmentation
        blocks = adapter.segment_blocks(structure, norm_files)
        block_names = [b.name for b in blocks]
        assert "0000-MAIN" in block_names
        assert "1000-READ" in block_names
        assert "2000-PROCESS" in block_names

        # Phase 3: CFG & Conditions
        edges, conditions, findings = adapter.extract_edges_and_conditions(blocks, structure, norm_files)

        # 0000-MAIN PERFORMS 1000-READ and 2000-PROCESS
        main_edges = [e for e in edges if e.source_name == "0000-MAIN"]
        main_perform_targets = {e.target_name for e in main_edges if e.edge_type == "PERFORMS"}
        assert "1000-READ" in main_perform_targets
        assert "2000-PROCESS" in main_perform_targets

        # 2000-PROCESS PERFORMS 1000-READ
        proc_edges = [e for e in edges if e.source_name == "2000-PROCESS"]
        proc_perform_targets = {e.target_name for e in proc_edges if e.edge_type == "PERFORMS"}
        assert "1000-READ" in proc_perform_targets

        # Check conditions in 2000-PROCESS (IF/ELSE and EVALUATE)
        cond_kinds = {c.kind for c in conditions}
        assert "IF" in cond_kinds
        assert "EVALUATE_WHEN" in cond_kinds

        # Phase 4: Graph Assembly
        graph = assemble_graph(blocks, edges, structure)
        assert "0000-MAIN" in graph.nodes
        assert "1000-READ" in graph.nodes
        assert len(graph.unreachable_blocks) == 0

    def test_acctmnt_pipeline_cycles_and_redefines(self, adapter):
        """ACCTMNT.cbl acceptance test (GO TO DEPENDING, cycles, REDEFINES, COMP-3)."""
        acctmnt_src = read_fixture("ACCTMNT.cbl")
        raw_files = [RawFile(path="ACCTMNT.cbl", content=acctmnt_src, role="main")]

        norm_files, _ = adapter.normalize(raw_files)
        structure = adapter.parse_structure(norm_files)

        # Check REDEFINES
        assert "WS-DATE" in structure.data_items
        assert structure.data_items["WS-DATE"].redefines == "WS-DATE-X"

        # Check COMP-3 (packed decimal)
        assert "ACCT-BAL" in structure.data_items
        assert structure.data_items["ACCT-BAL"].is_packed_decimal is True
        assert structure.data_items["ACCT-BAL"].usage == "COMP-3"

        blocks = adapter.segment_blocks(structure, norm_files)
        edges, conditions, findings = adapter.extract_edges_and_conditions(blocks, structure, norm_files)

        # Check GO TO DEPENDING edges from MENU
        gtd_edges = [e for e in edges if e.source_name == "MENU" and e.edge_type == "GOES_TO_DEPENDING"]
        gtd_targets = {e.target_name for e in gtd_edges}
        assert "DO-DEPOSIT" in gtd_targets
        assert "DO-WITHDRAW" in gtd_targets
        assert "SHOW-BAL" in gtd_targets

        # Check SEARCH AT END condition
        search_conds = [c for c in conditions if c.kind == "SEARCH_AT_END"]
        assert len(search_conds) >= 1

        # Check START-HERE falls through to MENU
        fall_throughs = [e for e in edges if e.source_name == "START-HERE" and e.edge_type == "FALLS_THROUGH"]
        assert len(fall_throughs) == 1
        assert fall_throughs[0].target_name == "MENU"

        # Phase 4: Graph Assembly & Cycle Detection
        graph = assemble_graph(blocks, edges, structure)
        cycle_findings = [f for f in graph.findings if f.kind == "CONTROL_CYCLE"]
        assert len(cycle_findings) >= 1
        # The menu loop forms an SCC
        multi_node_sccs = [scc for scc in graph.scc_list if len(scc) > 1]
        assert len(multi_node_sccs) >= 1
        assert "MENU" in multi_node_sccs[0]

    def test_deptrpt_fallback_segmentation(self, adapter):
        """DEPTRPT.cbl fallback segmentation for single-paragraph programs."""
        deptrpt_src = read_fixture("DEPTRPT.cbl")
        raw_files = [RawFile(path="DEPTRPT.cbl", content=deptrpt_src, role="main")]

        norm_files, _ = adapter.normalize(raw_files)
        structure = adapter.parse_structure(norm_files)
        assert len(structure.paragraphs) == 1

        # Segmentation should fall back to statement groups / inline loops
        blocks = adapter.segment_blocks(structure, norm_files)
        assert len(blocks) >= 2
        block_kinds = {b.kind for b in blocks}
        assert "loop" in block_kinds or "statement_group" in block_kinds

        # Check nested PERFORM UNTIL / VARYING conditions
        edges, conditions, _ = adapter.extract_edges_and_conditions(blocks, structure, norm_files)
        perform_conds = [c for c in conditions if c.kind == "PERFORM_UNTIL"]
        assert len(perform_conds) >= 1

    def test_malformed_input_partial_status(self, adapter):
        """A file with an unparseable or incomplete region yields parse_status=partial."""
        malformed_src = """       IDENTIFICATION DIVISION.
       PROGRAM-ID. MALFORMED.
       DATA DIVISION.
       WORKING-STORAGE SECTION.
       01  WS-CORRUPT-LINE $$$$ INVALID CHARS
       PROCEDURE DIVISION.
       START-P.
           DISPLAY "OK".
"""
        raw_files = [RawFile(path="MALFORMED.cbl", content=malformed_src, role="main")]
        norm_files, _ = adapter.normalize(raw_files)
        structure = adapter.parse_structure(norm_files)
        blocks = adapter.segment_blocks(structure, norm_files)
        assert len(blocks) >= 1
        # Pipeline continues and produces a usable graph without crashing
        edges, conditions, _ = adapter.extract_edges_and_conditions(blocks, structure, norm_files)
        graph = assemble_graph(blocks, edges, structure)
        assert "START-P" in graph.nodes

    def test_missing_copybook_warning(self, adapter):
        """Missing copybook is recorded as a warning finding and run continues."""
        src_with_missing_copy = """       IDENTIFICATION DIVISION.
       PROGRAM-ID. MISSINGCOPY.
       DATA DIVISION.
       WORKING-STORAGE SECTION.
       COPY NONEXISTENT.
       PROCEDURE DIVISION.
       MAIN-P.
           STOP RUN.
"""
        raw_files = [RawFile(path="TEST.cbl", content=src_with_missing_copy, role="main")]
        norm_files, findings = adapter.normalize(raw_files)
        missing_findings = [f for f in findings if f.kind == "MISSING_COPYBOOK"]
        assert len(missing_findings) == 1
        assert "NONEXISTENT" in missing_findings[0].message
