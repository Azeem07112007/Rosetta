"""Block-by-block LLM reasoning, Context Packet building, AST validation, and Complexity scoring."""
import hashlib
import json
from typing import Any, Dict, List, Optional, Set, Tuple

import structlog
from pydantic import BaseModel, Field

from app.analyzer.adapters.base import (
    Block,
    ExtractedCondition,
    FindingItem,
    GraphEdgeItem,
    StructureResult,
)
from app.analyzer.graph import AssembledGraph
from app.analyzer.llm.client import LLMClient

logger = structlog.get_logger()


# ==============================================================================
# Pydantic Schemas for Structured LLM Reasoning Output
# ==============================================================================


class BusinessRule(BaseModel):
    statement: str = Field(..., description="Concise statement of the business rule")
    lines: List[int] = Field(default_factory=list, description="Citations of line numbers inside this block")
    condition_ids: List[str] = Field(default_factory=list, description="Referenced condition identifiers")


class BlockReasoningOutput(BaseModel):
    purpose: str = Field(..., max_length=500, description="1-2 sentences summarizing the block's operational purpose")
    inputs: List[str] = Field(default_factory=list, description="Identifiers read or inspected by this block")
    outputs: List[str] = Field(default_factory=list, description="Identifiers updated, written, or assigned by this block")
    side_effects: List[str] = Field(default_factory=list, description="File I/O, database tables, display, or calls")
    business_rules: List[BusinessRule] = Field(default_factory=list, description="Extracted business rules with line citations")
    edge_cases: List[str] = Field(default_factory=list, description="Identified boundary conditions and edge cases")
    numeric_risks: List[str] = Field(default_factory=list, description="Numeric risks (truncation, rounding, packed decimal, sign)")
    confidence: str = Field(default="high", description="Confidence level: high, medium, low")
    unverified_claims: List[Dict[str, Any]] = Field(default_factory=list, description="Claims that failed validation")


# ==============================================================================
# Context Packet Builder (Phase 5)
# ==============================================================================


def build_context_packet(
    block: Block,
    structure: StructureResult,
    edges: List[GraphEdgeItem],
    conditions: List[ExtractedCondition],
    callee_summaries: Dict[str, str],
    token_budget: int = 4000,
) -> str:
    """Build a compact, delimited context packet for a single block."""
    # 1. Numbered source lines
    lines = block.source_text.splitlines()
    numbered_source = "\n".join(
        f"{block.start_line + i:04d}: {line}" for i, line in enumerate(lines)
    )

    # 2. Filtered Data Dictionary (only items referenced by this block)
    block_var_edges = [
        e.target_name for e in edges
        if e.source_name == block.name and e.edge_type in ("READS", "WRITES", "UPDATES")
    ]
    data_dict_lines = []
    for var in set(block_var_edges):
        item = structure.data_items.get(var)
        if item:
            info = f"{item.level:02d} {item.name}"
            if item.pic:
                info += f" PIC {item.pic}"
            if item.usage:
                info += f" USAGE {item.usage}"
            if item.redefines:
                info += f" REDEFINES {item.redefines}"
            if item.condition_88_values:
                info += f" [88 Values: {', '.join(item.condition_88_values)}]"
            data_dict_lines.append(info)

    data_dict_str = "\n".join(data_dict_lines) if data_dict_lines else "None"

    # 3. Callee Summaries
    callee_lines = []
    for e in edges:
        if e.source_name == block.name and e.edge_type in ("PERFORMS", "PERFORMS_THRU", "CALLS"):
            summary = callee_summaries.get(e.target_name)
            if summary:
                callee_lines.append(f"- {e.target_name}: {summary}")
    callee_str = "\n".join(callee_lines) if callee_lines else "None"

    # 4. Conditions in this block
    cond_lines = [
        f"- Line {c.start_line} [{c.kind}]: {c.normalized_predicate}"
        for c in conditions if c.block_name == block.name
    ]
    cond_str = "\n".join(cond_lines) if cond_lines else "None"

    packet = f"""<block_metadata>
Name: {block.name}
Kind: {block.kind}
Lines: {block.start_line} to {block.end_line}
</block_metadata>

<untrusted_source_code>
{numbered_source}
</untrusted_source_code>

<referenced_data_items>
{data_dict_str}
</referenced_data_items>

<known_conditions>
{cond_str}
</known_conditions>

<callee_summaries>
{callee_str}
</callee_summaries>
"""
    # Enforce approximate token budget truncation if unusually large
    if len(packet) > token_budget * 4:
        packet = packet[:token_budget * 4] + "\n[... TRUNCATED DUE TO BUDGET ...]\n"

    return packet


# ==============================================================================
# AST Hallucination Validator
# ==============================================================================


def validate_reasoning(
    result: Dict[str, Any],
    block: Block,
    structure: StructureResult,
    conditions: List[ExtractedCondition],
) -> Tuple[Dict[str, Any], List[str]]:
    """Validate that LLM citations strictly exist in the deterministic AST facts."""
    errors: List[str] = []
    unverified: List[Dict[str, Any]] = list(result.get("unverified_claims", []))

    valid_lines = range(block.start_line, block.end_line + 1)
    valid_identifiers = set(structure.data_items.keys()) | {p["name"] for p in structure.paragraphs}
    valid_cond_kinds = {c.kind for c in conditions if c.block_name == block.name}

    # 1. Validate Business Rules line citations
    valid_rules = []
    for rule in result.get("business_rules", []):
        rule_obj = rule if isinstance(rule, dict) else rule.model_dump()
        c_lines = rule_obj.get("lines", [])
        invalid_lines = [l for l in c_lines if l not in valid_lines]

        if invalid_lines:
            errors.append(f"Rule '{rule_obj.get('statement')}' cites lines {invalid_lines} outside block bounds [{block.start_line}-{block.end_line}].")
            unverified.append({"type": "invalid_line_citation", "rule": rule_obj, "invalid_lines": invalid_lines})
        else:
            valid_rules.append(rule_obj)
    result["business_rules"] = valid_rules

    # 2. Validate Input / Output Identifiers
    valid_inputs = []
    for inp in result.get("inputs", []):
        if inp.upper() in valid_identifiers or any(inp.upper() in item for item in valid_identifiers):
            valid_inputs.append(inp)
        else:
            errors.append(f"Input identifier '{inp}' does not exist in Data Division or Procedure Division.")
            unverified.append({"type": "hallucinated_input", "identifier": inp})
    result["inputs"] = valid_inputs

    valid_outputs = []
    for out in result.get("outputs", []):
        if out.upper() in valid_identifiers or any(out.upper() in item for item in valid_identifiers):
            valid_outputs.append(out)
        else:
            errors.append(f"Output identifier '{out}' does not exist in Data Division or Procedure Division.")
            unverified.append({"type": "hallucinated_output", "identifier": out})
    result["outputs"] = valid_outputs

    result["unverified_claims"] = unverified
    if unverified:
        result["confidence"] = "low" if len(unverified) > 2 else "medium"

    return result, errors


# ==============================================================================
# Complexity & Risk Scoring (Phase 6)
# ==============================================================================


def compute_complexity_and_risk(
    block: Block,
    conditions: List[ExtractedCondition],
    edges: List[GraphEdgeItem],
    graph: AssembledGraph,
    shared_mutables_threshold: int = 2,
    all_blocks: Optional[List[Block]] = None,
) -> Dict[str, Any]:
    """Compute Cyclomatic complexity, nesting depth, GO TO count, and composite risk ranking."""
    block_conds = [c for c in conditions if c.block_name == block.name]
    b_edges = [e for e in edges if e.source_name == block.name]

    # Cyclomatic complexity: 1 + decision points
    cyclomatic = 1 + len(block_conds)

    # Max nesting depth
    nesting_depth = max([c.nesting_depth for c in block_conds], default=0)

    # GO TO count & Fall-through count
    goto_count = len([e for e in b_edges if e.edge_type in ("GOES_TO", "GOES_TO_DEPENDING")])
    fall_through_count = len([e for e in b_edges if e.edge_type == "FALLS_THROUGH"])

    # PERFORM THRU range size
    thru_edges = [e for e in b_edges if e.edge_type == "PERFORMS_THRU"]
    max_thru_range = max([e.metadata.get("range_size", 1) for e in thru_edges], default=0)

    # ALTER presence
    has_alter = any(e.edge_type == "ALTERS" for e in b_edges)

    # SCC membership
    in_scc = any(block.name in scc for scc in graph.scc_list if len(scc) > 1)

    # Unreachable
    is_unreachable = block.name in graph.unreachable_blocks

    # Shared mutable data items written by this block and others
    writes = {e.target_name for e in b_edges if e.edge_type in ("WRITES", "UPDATES")}
    shared_mutables_count = 0
    if all_blocks:
        for var in writes:
            writer_count = sum(
                1 for e in edges if e.target_name == var and e.edge_type in ("WRITES", "UPDATES")
            )
            if writer_count >= shared_mutables_threshold:
                shared_mutables_count += 1

    # Composite Risk Formula (Ranked 0-100)
    # Score = min(100, 15*Cyclomatic + 10*Nesting + 12*GO_TOs + 20*ALTER + 15*SharedMutables + 25*InSCC)
    composite_score = min(
        100,
        15 * cyclomatic
        + 10 * nesting_depth
        + 12 * goto_count
        + (25 if has_alter else 0)
        + 15 * shared_mutables_count
        + (25 if in_scc else 0)
    )

    return {
        "cyclomatic_complexity": cyclomatic,
        "max_nesting_depth": nesting_depth,
        "goto_count": goto_count,
        "fall_through_count": fall_through_count,
        "max_thru_range": max_thru_range,
        "has_alter": has_alter,
        "in_scc": in_scc,
        "is_unreachable": is_unreachable,
        "shared_mutables_count": shared_mutables_count,
        "fan_in": graph.fan_in.get(block.name, 0),
        "fan_out": graph.fan_out.get(block.name, 0),
        "composite_risk_score": composite_score,
    }


# ==============================================================================
# Phase 5 Execution Engine: Leaves-First Reasoning
# ==============================================================================


async def analyze_blocks_leaf_first(
    blocks: List[Block],
    structure: StructureResult,
    edges: List[GraphEdgeItem],
    conditions: List[ExtractedCondition],
    graph: AssembledGraph,
    llm_client: LLMClient,
) -> Tuple[Dict[str, Dict[str, Any]], int, List[FindingItem]]:
    """Iterate through blocks in condensed leaf-first order, generating verified analyses."""
    block_map = {b.name: b for b in blocks}
    block_results: Dict[str, Dict[str, Any]] = {}
    callee_summaries: Dict[str, str] = {}
    total_tokens = 0
    findings: List[FindingItem] = []

    # Process each SCC unit in leaves-first topological order
    for scc in graph.topological_order:
        for b_name in scc:
            block = block_map.get(b_name)
            if not block:
                continue

            packet = build_context_packet(block, structure, edges, conditions, callee_summaries)
            prompt = f"Analyze code block '{block.name}':\n\n{packet}"

            # First LLM call
            raw_result, tokens = await llm_client.generate_json(prompt, BlockReasoningOutput)
            total_tokens += tokens

            # Validate against deterministic facts
            validated_result, validation_errors = validate_reasoning(raw_result, block, structure, conditions)

            # Retry once if validation failed
            if validation_errors:
                retry_prompt = (
                    f"{prompt}\n\n"
                    f"PREVIOUS ATTEMPT CONTAINED CITATION ERRORS:\n"
                    + "\n".join(f"- {e}" for e in validation_errors)
                    + "\nPlease fix the citations to strictly refer only to identifiers and line numbers within the block."
                )
                try:
                    retry_result, retry_tokens = await llm_client.generate_json(retry_prompt, BlockReasoningOutput)
                    total_tokens += retry_tokens
                    validated_result, _ = validate_reasoning(retry_result, block, structure, conditions)
                except Exception as e:
                    logger.warning("analyzer_validation_retry_failed", block=b_name, error=str(e))

            # Record any unverified findings
            if validated_result.get("unverified_claims"):
                findings.append(
                    FindingItem(
                        severity="warning",
                        kind="UNVERIFIED_LLM_CLAIM",
                        message=f"Block '{block.name}' contains {len(validated_result['unverified_claims'])} unverified LLM claims.",
                        block_name=block.name,
                    )
                )

            block_results[block.name] = validated_result
            callee_summaries[block.name] = validated_result.get("purpose", "")

    return block_results, total_tokens, findings
