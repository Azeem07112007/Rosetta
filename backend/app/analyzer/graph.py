"""Dependency and Control Flow Graph assembly, SCC detection, reachability, and topological sorting."""
from collections import defaultdict, deque
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Set, Tuple

from app.analyzer.adapters.base import (
    Block,
    FindingItem,
    GraphEdgeItem,
    StructureResult,
)


@dataclass
class NodeData:
    name: str
    node_type: str  # program, copybook, block, data_item, file, sql_table, external_program
    ref_id: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class AssembledGraph:
    nodes: Dict[str, NodeData]
    edges: List[GraphEdgeItem]
    scc_list: List[List[str]]  # Strongly connected components (cycles if len > 1)
    unreachable_blocks: Set[str]
    fan_in: Dict[str, int]
    fan_out: Dict[str, int]
    topological_order: List[List[str]]  # SCC units in leaf-first order for Phase 5
    findings: List[FindingItem]


def assemble_graph(
    blocks: List[Block],
    edges: List[GraphEdgeItem],
    structure: StructureResult,
) -> AssembledGraph:
    """Phase 4: Dependency Graph Assembly, SCC (Tarjan), reachability, fan-in/fan-out, top-sort."""
    nodes: Dict[str, NodeData] = {}
    findings: List[FindingItem] = []

    # 1. Register Nodes
    # Program node
    nodes[structure.program_name] = NodeData(name=structure.program_name, node_type="program")

    # Block nodes
    block_names = set()
    for b in blocks:
        block_names.add(b.name)
        nodes[b.name] = NodeData(
            name=b.name,
            node_type="block",
            metadata={"kind": b.kind, "start_line": b.start_line, "end_line": b.end_line},
        )

    # Data item nodes
    for name, item in structure.data_items.items():
        nodes[name] = NodeData(
            name=name,
            node_type="data_item",
            metadata={"level": item.level, "pic": item.pic, "is_packed": item.is_packed_decimal},
        )

    # File nodes
    for f in structure.files:
        nodes[f["name"]] = NodeData(name=f["name"], node_type="file")

    # SQL Table nodes
    for sql in structure.sql_blocks:
        for t in sql.target_tables:
            if t not in nodes:
                nodes[t] = NodeData(name=t, node_type="sql_table")

    # 2. Build Adjacency for Control Flow (Block -> Block)
    control_types = {"PERFORMS", "PERFORMS_THRU", "GOES_TO", "GOES_TO_DEPENDING", "FALLS_THROUGH"}
    adj: Dict[str, Set[str]] = {b: set() for b in block_names}
    rev_adj: Dict[str, Set[str]] = {b: set() for b in block_names}
    fan_in: Dict[str, int] = {b: 0 for b in block_names}
    fan_out: Dict[str, int] = {b: 0 for b in block_names}

    for e in edges:
        if e.source_name in block_names and e.target_name in block_names:
            if e.edge_type in control_types:
                adj[e.source_name].add(e.target_name)
                rev_adj[e.target_name].add(e.source_name)
                fan_out[e.source_name] += 1
                fan_in[e.target_name] += 1

    # 3. Tarjan's Strongly Connected Components Algorithm
    index = 0
    indices: Dict[str, int] = {}
    lowlinks: Dict[str, int] = {}
    on_stack: Set[str] = set()
    stack: List[str] = []
    sccs: List[List[str]] = []

    def strongconnect(v: str):
        nonlocal index
        indices[v] = index
        lowlinks[v] = index
        index += 1
        stack.append(v)
        on_stack.add(v)

        for w in adj[v]:
            if w not in indices:
                strongconnect(w)
                lowlinks[v] = min(lowlinks[v], lowlinks[w])
            elif w in on_stack:
                lowlinks[v] = min(lowlinks[v], indices[w])

        if lowlinks[v] == indices[v]:
            scc = []
            while True:
                w = stack.pop()
                on_stack.remove(w)
                scc.append(w)
                if w == v:
                    break
            sccs.append(scc)

    for b in block_names:
        if b not in indices:
            strongconnect(b)

    # Detect cycles (SCC with size > 1 or self-loop)
    for scc in sccs:
        is_cycle = len(scc) > 1 or (len(scc) == 1 and scc[0] in adj[scc[0]])
        if is_cycle:
            findings.append(
                FindingItem(
                    severity="warning",
                    kind="CONTROL_CYCLE",
                    message=f"Detected cyclic control flow loop across blocks: {', '.join(scc)}",
                    block_name=scc[0],
                )
            )

    # 4. Reachability Analysis (from entrypoint paragraph)
    entrypoint = blocks[0].name if blocks else None
    reachable: Set[str] = set()
    if entrypoint:
        queue = deque([entrypoint])
        reachable.add(entrypoint)
        while queue:
            curr = queue.popleft()
            for neighbor in adj[curr]:
                if neighbor not in reachable:
                    reachable.add(neighbor)
                    queue.append(neighbor)

    unreachable_blocks = block_names - reachable
    for u in unreachable_blocks:
        findings.append(
            FindingItem(
                severity="warning",
                kind="UNREACHABLE_BLOCK",
                message=f"Block '{u}' is unreachable from procedure entrypoint '{entrypoint}'.",
                block_name=u,
            )
        )

    # 5. Condensed DAG and Topological Sort (Leaves First for Phase 5)
    block_to_scc: Dict[str, int] = {}
    for scc_id, scc in enumerate(sccs):
        for b in scc:
            block_to_scc[b] = scc_id

    scc_adj: Dict[int, Set[int]] = {i: set() for i in range(len(sccs))}
    scc_in_degree: Dict[int, int] = {i: 0 for i in range(len(sccs))}

    for u in block_names:
        u_scc = block_to_scc[u]
        for v in adj[u]:
            v_scc = block_to_scc[v]
            if u_scc != v_scc and v_scc not in scc_adj[u_scc]:
                scc_adj[u_scc].add(v_scc)
                scc_in_degree[v_scc] += 1

    # Topological order over condensed graph
    zero_in = deque([s_id for s_id, deg in scc_in_degree.items() if deg == 0])
    forward_order: List[int] = []

    while zero_in:
        curr_scc = zero_in.popleft()
        forward_order.append(curr_scc)
        for nxt in scc_adj[curr_scc]:
            scc_in_degree[nxt] -= 1
            if scc_in_degree[nxt] == 0:
                zero_in.append(nxt)

    # For any remaining (e.g. disconnected) SCCs:
    for s_id in range(len(sccs)):
        if s_id not in forward_order:
            forward_order.append(s_id)

    # Leaf-first order (callees before callers): reverse of topological sort
    leaf_first_sccs = [sccs[s_id] for s_id in reversed(forward_order)]

    return AssembledGraph(
        nodes=nodes,
        edges=edges,
        scc_list=sccs,
        unreachable_blocks=unreachable_blocks,
        fan_in=fan_in,
        fan_out=fan_out,
        topological_order=leaf_first_sccs,
        findings=findings,
    )
