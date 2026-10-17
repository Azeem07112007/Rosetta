"""Serializers for exporting analysis runs to JSON, Markdown, Mermaid, DOT, and CSV."""
import csv
import io
import json
from typing import Any, Dict, List


def export_as_json(
    run_dict: Dict[str, Any],
    blocks: List[Dict[str, Any]],
    conditions: List[Dict[str, Any]],
    nodes: List[Dict[str, Any]],
    edges: List[Dict[str, Any]],
    findings: List[Dict[str, Any]],
) -> str:
    """Full architectural model serialized as indented JSON."""
    payload = {
        "run": run_dict,
        "blocks": blocks,
        "conditions": conditions,
        "graph": {"nodes": nodes, "edges": edges},
        "findings": findings,
    }
    return json.dumps(payload, indent=2, default=str)


def export_as_markdown(
    run_dict: Dict[str, Any],
    blocks: List[Dict[str, Any]],
    conditions: List[Dict[str, Any]],
    findings: List[Dict[str, Any]],
) -> str:
    """Human-readable Markdown audit report."""
    md = [
        f"# Rosetta Legacy Code Analysis: {run_dict.get('language', 'COBOL').upper()}",
        f"\n**Run ID:** `{run_dict.get('id')}`  ",
        f"**Status:** {run_dict.get('status')}  ",
        f"**Total Blocks:** {len(blocks)}  ",
        f"**Total Conditions:** {len(conditions)}  ",
        f"**Findings:** {len(findings)}\n",
        "## Top Risk Code Blocks\n",
        "| Block Name | Kind | Lines | Cyclomatic | Nesting | Risk Score |",
        "|---|---|---|---|---|---|",
    ]

    sorted_blocks = sorted(
        blocks,
        key=lambda b: b.get("complexity", {}).get("composite_risk_score", 0),
        reverse=True,
    )
    for b in sorted_blocks[:10]:
        comp = b.get("complexity", {})
        md.append(
            f"| `{b.get('name')}` | {b.get('kind')} | {b.get('start_line')}-{b.get('end_line')} | "
            f"{comp.get('cyclomatic_complexity', 1)} | {comp.get('max_nesting_depth', 0)} | "
            f"**{comp.get('composite_risk_score', 0)}/100** |"
        )

    md.append("\n## Key Diagnostic Findings\n")
    if not findings:
        md.append("_No critical risks or unverified claims detected._\n")
    else:
        for f in findings:
            md.append(f"- **[{f.get('severity', 'info').upper()}]** `{f.get('kind')}`: {f.get('message')}")

    md.append("\n## Condition Inventory Summary\n")
    md.append(f"Identified {len(conditions)} business and control decision points.\n")
    return "\n".join(md)


def export_as_mermaid(
    nodes: List[Dict[str, Any]],
    edges: List[Dict[str, Any]],
) -> str:
    """Mermaid flowchart diagram."""
    lines = ["flowchart TD"]

    # Add block nodes with clean styling
    for n in nodes:
        clean_name = n["name"].replace("-", "_").replace(".", "_")
        lines.append(f"    {clean_name}[\"{n['name']}\"]")

    for e in edges:
        src = e["source_name"].replace("-", "_").replace(".", "_") if "source_name" in e else str(e["source_node_id"])[:8]
        tgt = e["target_name"].replace("-", "_").replace(".", "_") if "target_name" in e else str(e["target_node_id"])[:8]
        edge_label = e.get("edge_type", "")
        lines.append(f"    {src} -->|{edge_label}| {tgt}")

    return "\n".join(lines)


def export_as_dot(
    nodes: List[Dict[str, Any]],
    edges: List[Dict[str, Any]],
) -> str:
    """Graphviz DOT format."""
    lines = [
        "digraph RosettaDependencyGraph {",
        "    rankdir=LR;",
        '    node [shape=box, fontname="Courier", style="rounded,filled", fillcolor="#f9f9f9"];',
        '    edge [fontname="Courier", fontsize=10];',
    ]

    for n in nodes:
        name = n["name"]
        lines.append(f'    "{name}" [label="{name}\\n({n.get("node_type", "node")})"];')

    for e in edges:
        src = e.get("source_name") or str(e["source_node_id"])[:8]
        tgt = e.get("target_name") or str(e["target_node_id"])[:8]
        label = e.get("edge_type", "")
        lines.append(f'    "{src}" -> "{tgt}" [label="{label}"];')

    lines.append("}")
    return "\n".join(lines)


def export_as_csv(conditions: List[Dict[str, Any]]) -> str:
    """CSV export of all extracted decision conditions."""
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow([
        "Kind",
        "Block Name",
        "Start Line",
        "End Line",
        "Normalized Predicate",
        "Operands",
        "Nesting Depth",
        "Plain English",
    ])

    for c in conditions:
        writer.writerow([
            c.get("kind"),
            c.get("block_name"),
            c.get("start_line"),
            c.get("end_line"),
            c.get("normalized_predicate"),
            ", ".join(c.get("operands", [])),
            c.get("nesting_depth", 0),
            c.get("plain_english", ""),
        ])

    return output.getvalue()
