"""COBOL Language Adapter implementing deterministic analysis phases 0-3."""
import hashlib
import re
from typing import Any, Dict, List, Optional, Set, Tuple

from app.analyzer.adapters.base import (
    Block,
    ConditionBranch,
    DataItem,
    ExtractedCondition,
    FindingItem,
    GraphEdgeItem,
    LanguageAdapter,
    NormalizedFile,
    NormalizedLine,
    RawFile,
    SqlBlock,
    StructureResult,
)


class CobolAdapter(LanguageAdapter):
    """Deterministic COBOL parser and analyzer."""

    # -------------------------------------------------------------------------
    # Phase 0: Normalization and Preprocessing
    # -------------------------------------------------------------------------

    def _is_fixed_format(self, content: str) -> bool:
        """Detect whether content conforms to fixed 80-column reference format."""
        if ">>SOURCE FORMAT IS FREE" in content.upper() or ">>SOURCE FREE" in content.upper():
            return False
        lines = content.splitlines()
        fixed_votes = 0
        inspected = 0
        for line in lines[:60]:
            if not line.strip():
                continue
            inspected += 1
            # In fixed format, lines often have sequence numbers in cols 1-6 and indicator in col 7
            if len(line) >= 7 and (line[:6].isdigit() or line[:6].isspace() or line[6] in (" ", "*", "/", "-", "D")):
                fixed_votes += 1
        return (fixed_votes / inspected > 0.6) if inspected > 0 else True

    def _expand_copybooks(
        self,
        raw_files: List[RawFile],
    ) -> Tuple[List[RawFile], List[FindingItem]]:
        """Resolve COPY and COPY ... REPLACING statements using uploaded copybooks."""
        findings: List[FindingItem] = []
        copybook_map: Dict[str, str] = {}

        # Index available copybooks (normalize names for case-insensitive lookup)
        for rf in raw_files:
            clean_name = rf.path.replace("\\", "/").split("/")[-1].upper()
            copybook_map[clean_name] = rf.content
            base_name = clean_name.rsplit(".", 1)[0]
            copybook_map[base_name] = rf.content

        expanded_files: List[RawFile] = []
        copy_pattern = re.compile(
            r"^\s*COPY\s+(?:[\"']?([A-Za-z0-9_-]+)[\"']?)(?:\s+REPLACING\s+(.+?))?\s*\.\s*$",
            re.IGNORECASE | re.MULTILINE,
        )

        for rf in raw_files:
            if rf.role == "copybook":
                expanded_files.append(rf)
                continue

            content = rf.content
            has_copy = copy_pattern.search(content)
            if not has_copy:
                expanded_files.append(rf)
                continue

            def replace_copy(match: re.Match) -> str:
                cb_name = match.group(1).upper()
                replacements_str = match.group(2)

                # Look up copybook
                cb_content = copybook_map.get(cb_name) or copybook_map.get(f"{cb_name}.CPY") or copybook_map.get(f"{cb_name}.CBL")
                if cb_content is None:
                    findings.append(
                        FindingItem(
                            severity="warning",
                            kind="MISSING_COPYBOOK",
                            message=f"Copybook '{cb_name}' could not be resolved from uploaded files.",
                        )
                    )
                    return f"      *> MISSING COPYBOOK: {cb_name}\n"

                # Apply REPLACING rules if present
                resolved = cb_content
                if replacements_str:
                    # Match pairs like ==old== BY ==new== or old BY new
                    pair_re = re.compile(
                        r"(?:==(.*?)==|([A-Za-z0-9_-]+))\s+BY\s+(?:==(.*?)==|([A-Za-z0-9_-]+))",
                        re.IGNORECASE,
                    )
                    for p in pair_re.finditer(replacements_str):
                        src = (p.group(1) or p.group(2)).strip()
                        dst = (p.group(3) or p.group(4)).strip()
                        resolved = resolved.replace(src, dst)

                return f"      *> BEGIN COPYBOOK {cb_name}\n{resolved}\n      *> END COPYBOOK {cb_name}\n"

            expanded_content = copy_pattern.sub(replace_copy, content)
            expanded_files.append(
                RawFile(
                    path=rf.path,
                    content=expanded_content,
                    role=rf.role,
                )
            )

        return expanded_files, findings

    def normalize(self, files: List[RawFile]) -> Tuple[List[NormalizedFile], List[FindingItem]]:
        """Phase 0: Format detection, comment/continuation handling, copybook resolution, SHA256."""
        expanded_files, copy_findings = self._expand_copybooks(files)
        normalized_files: List[NormalizedFile] = []

        for rf in expanded_files:
            sha256 = hashlib.sha256(rf.content.encode("utf-8")).hexdigest()
            is_fixed = self._is_fixed_format(rf.content)
            lines = rf.content.splitlines()

            norm_lines: List[NormalizedLine] = []
            stitched_lines: List[str] = []

            for idx, raw_line in enumerate(lines, start=1):
                if is_fixed:
                    # Fixed Format:
                    # 1-6: Sequence, 7: Indicator, 8-72: Area A & B, 73-80: Identification
                    indicator = raw_line[6] if len(raw_line) >= 7 else " "
                    code_part = raw_line[7:72] if len(raw_line) >= 8 else ""

                    if indicator in ("*", "/"):
                        norm_lines.append(NormalizedLine(idx, code_part.strip(), is_comment=True))
                        stitched_lines.append(f"*> {code_part.strip()}")
                    elif indicator == "-":
                        # Continuation line: append to previous code line
                        clean_text = code_part.lstrip()
                        if clean_text.startswith(('"', "'")):
                            clean_text = clean_text[1:]
                        if stitched_lines:
                            stitched_lines[-1] = stitched_lines[-1].rstrip() + clean_text
                        norm_lines.append(NormalizedLine(idx, clean_text, is_continuation=True))
                    elif indicator.upper() == "D":
                        # Debugging line: treat as comment in normal analysis
                        norm_lines.append(NormalizedLine(idx, code_part.strip(), is_comment=True))
                        stitched_lines.append(f"*> DEBUG: {code_part.strip()}")
                    else:
                        norm_lines.append(NormalizedLine(idx, code_part))
                        stitched_lines.append(code_part)
                else:
                    # Free format
                    stripped = raw_line.strip()
                    if stripped.startswith("*>") or stripped.startswith("*"):
                        norm_lines.append(NormalizedLine(idx, stripped, is_comment=True))
                        stitched_lines.append(stripped)
                    else:
                        norm_lines.append(NormalizedLine(idx, raw_line))
                        stitched_lines.append(raw_line)

            normalized_content = "\n".join(stitched_lines)
            normalized_files.append(
                NormalizedFile(
                    path=rf.path,
                    role=rf.role,
                    sha256=sha256,
                    lines=norm_lines,
                    raw_content=rf.content,
                    normalized_content=normalized_content,
                    format_type="fixed" if is_fixed else "free",
                )
            )

        return normalized_files, copy_findings

    # -------------------------------------------------------------------------
    # Phase 1: Structural Parsing
    # -------------------------------------------------------------------------

    def parse_structure(self, normalized_files: List[NormalizedFile]) -> StructureResult:
        """Phase 1: Extracts Divisions, Sections, Paragraphs, Data Hierarchy, SQL/CICS blocks."""
        main_files = [f for f in normalized_files if f.role == "main"]
        target_file = main_files[0] if main_files else normalized_files[0]

        program_name = "UNKNOWN"
        divisions: Dict[str, Dict[str, int]] = {}
        sections: List[Dict[str, Any]] = []
        paragraphs: List[Dict[str, Any]] = []
        data_items: Dict[str, DataItem] = {}
        sql_blocks: List[SqlBlock] = []
        files_declared: List[Dict[str, Any]] = []
        findings: List[FindingItem] = []

        current_division: Optional[str] = None
        current_section: Optional[str] = None
        current_data_item: Optional[DataItem] = None
        data_item_stack: List[DataItem] = []

        lines = target_file.lines
        total_lines = len(lines)

        in_sql_cics = False
        sql_kind = ""
        sql_start_line = 0
        sql_buffer: List[str] = []

        for idx, nline in enumerate(lines):
            line_no = nline.original_line_number
            raw_text = nline.text
            clean_text = raw_text.strip().upper()

            if nline.is_comment or not clean_text:
                continue

            # Check EXEC SQL / EXEC CICS
            if clean_text.startswith("EXEC SQL") or clean_text.startswith("EXEC CICS"):
                in_sql_cics = True
                sql_kind = "SQL" if "SQL" in clean_text else "CICS"
                sql_start_line = line_no
                sql_buffer = [raw_text]
                if "END-EXEC" in clean_text:
                    in_sql_cics = False
                    sql_blocks.append(
                        SqlBlock(
                            kind=sql_kind,
                            start_line=sql_start_line,
                            end_line=line_no,
                            raw_statement=raw_text,
                            target_tables=self._extract_sql_tables(raw_text),
                        )
                    )
                continue

            if in_sql_cics:
                sql_buffer.append(raw_text)
                if "END-EXEC" in clean_text:
                    in_sql_cics = False
                    stmt = "\n".join(sql_buffer)
                    sql_blocks.append(
                        SqlBlock(
                            kind=sql_kind,
                            start_line=sql_start_line,
                            end_line=line_no,
                            raw_statement=stmt,
                            target_tables=self._extract_sql_tables(stmt),
                        )
                    )
                continue

            # Program-ID
            if "PROGRAM-ID." in clean_text:
                match = re.search(r"PROGRAM-ID\.\s*([A-Za-z0-9_-]+)", clean_text)
                if match:
                    program_name = match.group(1)

            # Division detection
            div_match = re.search(
                r"^(IDENTIFICATION|ENVIRONMENT|DATA|PROCEDURE)\s+DIVISION",
                clean_text,
            )
            if div_match:
                div_name = div_match.group(1)
                if current_division and current_division in divisions:
                    divisions[current_division]["end"] = line_no - 1
                current_division = div_name
                divisions[div_name] = {"start": line_no, "end": total_lines}
                current_section = None
                continue

            # Data Division parsing
            if current_division == "DATA":
                # FD / SD detection
                if clean_text.startswith("FD ") or clean_text.startswith("SD "):
                    fd_match = re.search(r"^(?:FD|SD)\s+([A-Za-z0-9_-]+)", clean_text)
                    if fd_match:
                        files_declared.append({"name": fd_match.group(1), "line": line_no})
                    continue

                # Data item detection (levels 01-49, 77, 88)
                data_match = re.match(r"^(\d{1,2})\s+([A-Za-z0-9_-]+)(.*)$", clean_text)
                if data_match:
                    level = int(data_match.group(1))
                    item_name = data_match.group(2)
                    rest = data_match.group(3)

                    # Extract PIC
                    pic: Optional[str] = None
                    pic_match = re.search(r"(?:PIC|PICTURE)\s+(?:IS\s+)?([X9SAVZ\(\)\$\*\+\-\.,CRDB]+)", rest)
                    if pic_match:
                        pic = pic_match.group(1).rstrip(".")

                    # Extract USAGE
                    usage: Optional[str] = None
                    is_packed = False
                    if "COMP-3" in rest or "COMPUTATIONAL-3" in rest or "PACKED-DECIMAL" in rest:
                        usage = "COMP-3"
                        is_packed = True
                    elif "COMP-4" in rest or "BINARY" in rest:
                        usage = "COMP-4"
                    elif "COMP-1" in rest:
                        usage = "COMP-1"
                    elif "COMP-2" in rest:
                        usage = "COMP-2"
                    elif "COMP" in rest or "COMPUTATIONAL" in rest:
                        usage = "COMP"
                    elif "DISPLAY" in rest:
                        usage = "DISPLAY"

                    # REDEFINES
                    redefines: Optional[str] = None
                    redef_match = re.search(r"REDEFINES\s+([A-Za-z0-9_-]+)", rest)
                    if redef_match:
                        redefines = redef_match.group(1)

                    # OCCURS
                    occurs: Optional[int] = None
                    occ_match = re.search(r"OCCURS\s+(\d+)", rest)
                    if occ_match:
                        occurs = int(occ_match.group(1))

                    # 88 Condition values
                    val_88s: List[str] = []
                    if level == 88:
                        val_match = re.search(r"(?:VALUE|VALUES)\s+(?:IS\s+|ARE\s+)?(.+)", rest)
                        if val_match:
                            val_str = val_match.group(1).rstrip(".")
                            val_88s = [v.strip().strip("'\"") for v in val_str.split()]
                        if current_data_item:
                            current_data_item.condition_88_values.extend(val_88s)

                    item = DataItem(
                        name=item_name,
                        level=level,
                        pic=pic,
                        usage=usage,
                        is_packed_decimal=is_packed,
                        redefines=redefines,
                        occurs=occurs,
                        condition_88_values=val_88s,
                        line_number=line_no,
                        is_group=(pic is None and level not in (77, 88)),
                    )

                    # Manage hierarchy stack
                    if level == 88:
                        item.parent_name = current_data_item.name if current_data_item else None
                    else:
                        while data_item_stack and data_item_stack[-1].level >= level:
                            data_item_stack.pop()
                        if data_item_stack:
                            item.parent_name = data_item_stack[-1].name
                            data_item_stack[-1].children.append(item_name)
                        data_item_stack.append(item)
                        current_data_item = item

                    data_items[item_name] = item
                continue

            # Procedure Division parsing
            if current_division == "PROCEDURE":
                # Section detection: NAME SECTION.
                sec_match = re.match(r"^([A-Za-z0-9_-]+)\s+SECTION\s*\.", clean_text)
                if sec_match:
                    sec_name = sec_match.group(1)
                    if sections:
                        sections[-1]["end"] = line_no - 1
                    current_section = sec_name
                    sections.append({"name": sec_name, "start": line_no, "end": total_lines})
                    continue

                # Paragraph detection: NAME. (at Area A / col 8-11 or start of line)
                para_match = re.match(r"^([A-Za-z0-9_-]+)\s*\.\s*$", clean_text)
                if para_match and not clean_text.startswith(("EXIT", "STOP", "GOBACK")):
                    para_name = para_match.group(1)
                    if paragraphs:
                        paragraphs[-1]["end"] = line_no - 1
                    paragraphs.append(
                        {
                            "name": para_name,
                            "section": current_section,
                            "start": line_no,
                            "end": total_lines,
                        }
                    )

        # Close out last sections/paragraphs
        if paragraphs:
            paragraphs[-1]["end"] = divisions.get("PROCEDURE", {}).get("end", total_lines)
        if sections:
            sections[-1]["end"] = divisions.get("PROCEDURE", {}).get("end", total_lines)

        return StructureResult(
            program_name=program_name,
            divisions=divisions,
            sections=sections,
            paragraphs=paragraphs,
            data_items=data_items,
            sql_blocks=sql_blocks,
            files=files_declared,
            parse_status="complete" if divisions.get("PROCEDURE") else "partial",
            findings=findings,
        )

    def _extract_sql_tables(self, stmt: str) -> List[str]:
        """Extract table names from embedded SQL statement."""
        tables = set()
        for pattern in (r"FROM\s+([A-Za-z0-9_]+)", r"INTO\s+([A-Za-z0-9_]+)", r"UPDATE\s+([A-Za-z0-9_]+)"):
            for m in re.finditer(pattern, stmt, re.IGNORECASE):
                tables.add(m.group(1).upper())
        return list(tables)

    # -------------------------------------------------------------------------
    # Phase 2: Block Segmentation
    # -------------------------------------------------------------------------

    def segment_blocks(
        self,
        structure: StructureResult,
        normalized_files: List[NormalizedFile],
    ) -> List[Block]:
        """Phase 2: Segment code into Paragraphs or Sections, with statement-group fallback."""
        main_files = [f for f in normalized_files if f.role == "main"]
        target_file = main_files[0] if main_files else normalized_files[0]
        blocks: List[Block] = []

        # Case 1: Standard Programs with multiple paragraphs, or single paragraph with no inline loops
        has_inline_loop = any("END-PERFORM" in nl.text.upper() for nl in target_file.lines)
        if len(structure.paragraphs) > 1 or (len(structure.paragraphs) == 1 and not has_inline_loop):
            for p in structure.paragraphs:
                p_lines = [
                    nl.text for nl in target_file.lines
                    if p["start"] <= nl.original_line_number <= p["end"]
                ]
                source_text = "\n".join(p_lines)
                raw_hash = hashlib.sha256(source_text.encode("utf-8")).hexdigest()

                blocks.append(
                    Block(
                        name=p["name"],
                        kind="paragraph",
                        start_line=p["start"],
                        end_line=p["end"],
                        file_path=target_file.path,
                        raw_hash=raw_hash,
                        source_text=source_text,
                        parent_name=p["section"],
                    )
                )
            return blocks

        # Case 2: Monolithic Program with <= 1 paragraph (Fallback segmentation)
        # e.g., DEPTRPT.cbl where logic is structured in inline PERFORM loops & statement clusters
        proc_div = structure.divisions.get("PROCEDURE")
        start_line = proc_div["start"] if proc_div else 1
        end_line = proc_div["end"] if proc_div else len(target_file.lines)

        current_block_lines: List[NormalizedLine] = []
        current_block_start = start_line
        block_idx = 1
        in_inline_perform = False
        loop_depth = 0

        for nl in target_file.lines:
            if not (start_line <= nl.original_line_number <= end_line):
                continue
            clean = nl.text.strip().upper()
            if nl.is_comment or not clean:
                continue

            # Detect inline PERFORM start
            if re.match(r"^PERFORM\s+(?:UNTIL|VARYING)", clean) and "THRU" not in clean:
                if current_block_lines and not in_inline_perform:
                    text = "\n".join(l.text for l in current_block_lines)
                    blocks.append(
                        Block(
                            name=f"BLOCK-{block_idx:03d}",
                            kind="statement_group",
                            start_line=current_block_start,
                            end_line=nl.original_line_number - 1,
                            file_path=target_file.path,
                            raw_hash=hashlib.sha256(text.encode("utf-8")).hexdigest(),
                            source_text=text,
                        )
                    )
                    block_idx += 1
                    current_block_lines = []
                    current_block_start = nl.original_line_number

                in_inline_perform = True
                loop_depth += 1

            current_block_lines.append(nl)

            # Detect inline PERFORM end
            if "END-PERFORM" in clean:
                loop_depth -= 1
                if loop_depth <= 0:
                    in_inline_perform = False
                    loop_depth = 0
                    text = "\n".join(l.text for l in current_block_lines)
                    blocks.append(
                        Block(
                            name=f"LOOP-{block_idx:03d}",
                            kind="loop",
                            start_line=current_block_start,
                            end_line=nl.original_line_number,
                            file_path=target_file.path,
                            raw_hash=hashlib.sha256(text.encode("utf-8")).hexdigest(),
                            source_text=text,
                        )
                    )
                    block_idx += 1
                    current_block_lines = []
                    current_block_start = nl.original_line_number + 1

        # Flush remaining lines
        if current_block_lines:
            text = "\n".join(l.text for l in current_block_lines)
            blocks.append(
                Block(
                    name=f"BLOCK-{block_idx:03d}",
                    kind="statement_group",
                    start_line=current_block_start,
                    end_line=current_block_lines[-1].original_line_number,
                    file_path=target_file.path,
                    raw_hash=hashlib.sha256(text.encode("utf-8")).hexdigest(),
                    source_text=text,
                )
            )

        return blocks

    # -------------------------------------------------------------------------
    # Phase 3: Control Flow, Data Flow, Conditions
    # -------------------------------------------------------------------------

    def extract_edges_and_conditions(
        self,
        blocks: List[Block],
        structure: StructureResult,
        normalized_files: List[NormalizedFile],
    ) -> Tuple[List[GraphEdgeItem], List[ExtractedCondition], List[FindingItem]]:
        """Phase 3: Typed CFG & Data Flow edges, conditions extraction, and risk findings."""
        edges: List[GraphEdgeItem] = []
        conditions: List[ExtractedCondition] = []
        findings: List[FindingItem] = []

        block_names = [b.name for b in blocks]
        block_name_set = set(block_names)

        # 1. Sequential Fall-Through Edges between consecutive paragraphs
        for idx in range(len(blocks) - 1):
            curr_b = blocks[idx]
            next_b = blocks[idx + 1]

            # Check if curr_b ends unconditionally
            last_lines = [l.strip().upper() for l in curr_b.source_text.splitlines() if l.strip()]
            ends_unconditional = False
            for line in reversed(last_lines[-3:]):
                if line.startswith(("STOP RUN", "GOBACK", "EXIT PROGRAM")) or re.match(r"^GO\s+TO\s+[A-Za-z0-9_-]+\s*\.?$", line):
                    ends_unconditional = True
                    break

            if not ends_unconditional:
                edges.append(
                    GraphEdgeItem(
                        source_name=curr_b.name,
                        target_name=next_b.name,
                        edge_type="FALLS_THROUGH",
                        source_line=curr_b.end_line,
                        is_conditional=False,
                    )
                )

        # 2. Block-by-block statement and condition extraction
        for block in blocks:
            b_lines = block.source_text.splitlines()
            curr_line_no = block.start_line

            # Multi-line GO TO DEPENDING check across block
            gtd_targets_handled = set()
            for m in re.finditer(r"GO\s+TO\s+(.+?)\s+DEPENDING\s+ON\s+([A-Za-z0-9_-]+)", block.source_text, re.IGNORECASE | re.DOTALL):
                targets = [t.strip().rstrip(".") for t in m.group(1).split() if t.strip()]
                var_dep = m.group(2)
                for b_idx, t in enumerate(targets, start=1):
                    if t in block_name_set:
                        gtd_targets_handled.add(t)
                        edges.append(
                            GraphEdgeItem(
                                source_name=block.name,
                                target_name=t,
                                edge_type="GOES_TO_DEPENDING",
                                source_line=block.start_line,
                                is_conditional=True,
                                metadata={"branch_index": b_idx, "variable": var_dep},
                            )
                        )
                conditions.append(
                    ExtractedCondition(
                        kind="GO_TO_DEPENDING",
                        start_line=block.start_line,
                        end_line=block.end_line,
                        raw_expression=m.group(0).strip(),
                        normalized_predicate=f"{var_dep} IN (1..{len(targets)})",
                        operands=[var_dep],
                        branches=[ConditionBranch(branch=f"index_{i}", target_name=t) for i, t in enumerate(targets, 1)],
                        block_name=block.name,
                    )
                )
                findings.append(
                    FindingItem(
                        severity="info",
                        kind="GO_TO_DEPENDING",
                        message=f"Block '{block.name}' uses GO TO DEPENDING with {len(targets)} targets.",
                        line_ranges=[[block.start_line, block.end_line]],
                        block_name=block.name,
                    )
                )

            # Multi-line PERFORM UNTIL / VARYING check across block
            for um in re.finditer(r"UNTIL\s+([^\.\n]+(?:\n\s+[^\.\n]+)*)", block.source_text, re.IGNORECASE):
                u_expr = um.group(1).strip().rstrip(".")
                if u_expr:
                    conditions.append(
                        ExtractedCondition(
                            kind="PERFORM_UNTIL",
                            start_line=block.start_line,
                            end_line=block.end_line,
                            raw_expression=u_expr,
                            normalized_predicate=u_expr,
                            operands=[w for w in re.findall(r"[A-Za-z0-9_-]+", u_expr) if w in structure.data_items],
                            block_name=block.name,
                        )
                    )

            # Multi-line SEARCH AT END check across block
            if "SEARCH" in block.source_text.upper() and "AT END" in block.source_text.upper():
                conditions.append(
                    ExtractedCondition(
                        kind="SEARCH_AT_END",
                        start_line=block.start_line,
                        end_line=block.end_line,
                        raw_expression="SEARCH ... AT END",
                        normalized_predicate="TABLE EXHAUSTED",
                        block_name=block.name,
                    )
                )

            for l_idx, raw_l in enumerate(b_lines):
                line_no = block.start_line + l_idx
                stmt = raw_l.strip().upper()

                # --- PERFORM / PERFORM THRU ---
                perform_match = re.search(r"\bPERFORM\s+([A-Za-z0-9_-]+)(?:\s+THRU\s+([A-Za-z0-9_-]+))?", stmt)
                if perform_match:
                    target_1 = perform_match.group(1)
                    target_2 = perform_match.group(2)

                    if target_2:
                        # PERFORM THRU: resolve all paragraphs in range
                        if target_1 in block_name_set and target_2 in block_name_set:
                            idx1 = block_names.index(target_1)
                            idx2 = block_names.index(target_2)
                            thru_range = block_names[min(idx1, idx2):max(idx1, idx2) + 1]
                            for t in thru_range:
                                edges.append(
                                    GraphEdgeItem(
                                        source_name=block.name,
                                        target_name=t,
                                        edge_type="PERFORMS_THRU",
                                        source_line=line_no,
                                        is_conditional=("UNTIL" in stmt or "VARYING" in stmt),
                                        metadata={"start": target_1, "end": target_2, "range_size": len(thru_range)},
                                    )
                                )
                    elif target_1 in block_name_set:
                        edges.append(
                            GraphEdgeItem(
                                source_name=block.name,
                                target_name=target_1,
                                edge_type="PERFORMS",
                                source_line=line_no,
                                is_conditional=("UNTIL" in stmt or "VARYING" in stmt),
                            )
                        )

                # --- Standard GO TO ---
                if "GO TO" in stmt and "DEPENDING" not in stmt:
                    goto_match = re.search(r"GO\s+TO\s+([A-Za-z0-9_-]+)", stmt)
                    if goto_match:
                        target = goto_match.group(1)
                        if target in block_name_set and target not in gtd_targets_handled:
                            edges.append(
                                GraphEdgeItem(
                                    source_name=block.name,
                                    target_name=target,
                                    edge_type="GOES_TO",
                                    source_line=line_no,
                                    is_conditional=("IF" in stmt or "WHEN" in stmt),
                                )
                            )

                # --- ALTER statement ---
                if re.search(r"\bALTER\s+([A-Za-z0-9_-]+)\s+TO\s+PROCEED\s+TO\s+([A-Za-z0-9_-]+)", stmt):
                    alter_match = re.search(r"\bALTER\s+([A-Za-z0-9_-]+)\s+TO\s+PROCEED\s+TO\s+([A-Za-z0-9_-]+)", stmt)
                    if alter_match:
                        p1, p2 = alter_match.group(1), alter_match.group(2)
                        edges.append(
                            GraphEdgeItem(
                                source_name=block.name,
                                target_name=p1,
                                edge_type="ALTERS",
                                source_line=line_no,
                                metadata={"proceed_to": p2},
                            )
                        )
                        findings.append(
                            FindingItem(
                                severity="critical",
                                kind="ALTER_FOUND",
                                message=f"Block '{block.name}' alters control flow of '{p1}' to proceed to '{p2}'.",
                                line_ranges=[[line_no, line_no]],
                                block_name=block.name,
                            )
                        )

                # --- CALL statement (Static vs Dynamic) ---
                call_match = re.search(r"\bCALL\s+(?:[\"']([A-Za-z0-9_-]+)[\"']|([A-Za-z0-9_-]+))", stmt)
                if call_match:
                    static_target = call_match.group(1)
                    dyn_target = call_match.group(2)
                    if static_target:
                        edges.append(
                            GraphEdgeItem(
                                source_name=block.name,
                                target_name=static_target,
                                edge_type="CALLS",
                                source_line=line_no,
                            )
                        )
                    elif dyn_target:
                        edges.append(
                            GraphEdgeItem(
                                source_name=block.name,
                                target_name=f"DYNAMIC({dyn_target})",
                                edge_type="CALLS_DYNAMIC",
                                source_line=line_no,
                                metadata={"identifier": dyn_target},
                            )
                        )
                        findings.append(
                            FindingItem(
                                severity="warning",
                                kind="DYNAMIC_CALL",
                                message=f"Block '{block.name}' performs dynamic CALL via variable '{dyn_target}'.",
                                line_ranges=[[line_no, line_no]],
                                block_name=block.name,
                            )
                        )

                # --- IF / ELSE Conditions ---
                if re.match(r"^IF\s+", stmt):
                    cond_expr = stmt[3:].rstrip(".")
                    operands = [w for w in re.findall(r"[A-Za-z0-9_-]+", cond_expr) if w in structure.data_items]
                    conditions.append(
                        ExtractedCondition(
                            kind="IF",
                            start_line=line_no,
                            end_line=line_no,
                            raw_expression=cond_expr,
                            normalized_predicate=cond_expr,
                            operands=operands,
                            branches=[ConditionBranch(branch="then"), ConditionBranch(branch="else")],
                            block_name=block.name,
                        )
                    )

                # --- EVALUATE / WHEN Conditions ---
                if "WHEN" in stmt and "EVALUATE" not in stmt:
                    when_expr = stmt.replace("WHEN", "").strip().rstrip(".")
                    conditions.append(
                        ExtractedCondition(
                            kind="EVALUATE_WHEN",
                            start_line=line_no,
                            end_line=line_no,
                            raw_expression=stmt,
                            normalized_predicate=when_expr,
                            operands=[w for w in re.findall(r"[A-Za-z0-9_-]+", when_expr) if w in structure.data_items],
                            branches=[ConditionBranch(branch="when_branch")],
                            block_name=block.name,
                        )
                    )

                # --- PERFORM UNTIL / VARYING Conditions ---
                if "PERFORM" in stmt and "UNTIL" in stmt:
                    until_match = re.search(r"UNTIL\s+(.+)$", stmt)
                    if until_match:
                        u_expr = until_match.group(1).rstrip(".")
                        conditions.append(
                            ExtractedCondition(
                                kind="PERFORM_UNTIL",
                                start_line=line_no,
                                end_line=line_no,
                                raw_expression=u_expr,
                                normalized_predicate=u_expr,
                                operands=[w for w in re.findall(r"[A-Za-z0-9_-]+", u_expr) if w in structure.data_items],
                                block_name=block.name,
                            )
                        )

                # --- SEARCH AT END Condition ---
                if "SEARCH" in stmt and "AT END" in stmt:
                    conditions.append(
                        ExtractedCondition(
                            kind="SEARCH_AT_END",
                            start_line=line_no,
                            end_line=line_no,
                            raw_expression=stmt,
                            normalized_predicate="TABLE EXHAUSTED",
                            block_name=block.name,
                        )
                    )

                # --- ON SIZE ERROR ---
                if "ON SIZE ERROR" in stmt:
                    conditions.append(
                        ExtractedCondition(
                            kind="ON_SIZE_ERROR",
                            start_line=line_no,
                            end_line=line_no,
                            raw_expression="ON SIZE ERROR",
                            normalized_predicate="NUMERIC OVERFLOW / TRUNCATION",
                            block_name=block.name,
                        )
                    )

                # --- Data Item References (READS / WRITES) ---
                for item_name, item in structure.data_items.items():
                    if item.level == 88:
                        continue
                    if re.search(rf"\b{item_name}\b", stmt):
                        is_write = False
                        if re.search(rf"MOVE\s+.*?\s+TO\s+.*?\b{item_name}\b", stmt):
                            is_write = True
                        elif re.search(rf"(?:ADD|SUBTRACT|MULTIPLY|DIVIDE)\s+.*?\s+GIVING\s+\b{item_name}\b", stmt):
                            is_write = True
                        elif re.search(rf"ADD\s+.*?\s+TO\s+\b{item_name}\b", stmt):
                            is_write = True
                        elif re.search(rf"COMPUTE\s+\b{item_name}\b\s*=", stmt):
                            is_write = True
                        elif re.search(rf"READ\s+.*?\s+INTO\s+\b{item_name}\b", stmt):
                            is_write = True

                        edges.append(
                            GraphEdgeItem(
                                source_name=block.name,
                                target_name=item_name,
                                edge_type="WRITES" if is_write else "READS",
                                source_line=line_no,
                            )
                        )

                        # Check for packed decimal risk
                        if item.is_packed_decimal:
                            findings.append(
                                FindingItem(
                                    severity="info",
                                    kind="PACKED_DECIMAL_RISK",
                                    message=f"Block '{block.name}' accesses COMP-3 (packed decimal) item '{item_name}'.",
                                    line_ranges=[[line_no, line_no]],
                                    block_name=block.name,
                                )
                            )

        # 3. Add Data Division REDEFINES edges
        for item_name, item in structure.data_items.items():
            if item.redefines:
                edges.append(
                    GraphEdgeItem(
                        source_name=item_name,
                        target_name=item.redefines,
                        edge_type="REDEFINES",
                        source_line=item.line_number,
                    )
                )

        return edges, conditions, findings
