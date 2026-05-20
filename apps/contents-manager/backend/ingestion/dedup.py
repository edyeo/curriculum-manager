"""Dedup Checker — exact name match against existing KG"""
from typing import Literal

import file_db
from pydantic import BaseModel

from .extractor import ExtractedEdge, ExtractedNode


class NodeDedupResult(BaseModel):
    name: str
    type: str
    status: Literal["new", "exact_duplicate"]
    decision: Literal["add", "skip"]
    matched_node_id: str | None = None


class EdgeDedupResult(BaseModel):
    source_name: str
    target_name: str
    relation: str
    status: Literal["new", "exact_duplicate"]
    decision: Literal["add", "skip"]


class DedupReport(BaseModel):
    nodes: list[NodeDedupResult]
    edges: list[EdgeDedupResult]


def check(
    extracted_nodes: list[ExtractedNode],
    extracted_edges: list[ExtractedEdge],
) -> DedupReport:
    existing_nodes = file_db.read_nodes()
    existing_edges = file_db.read_edges()

    existing_by_name: dict[str, str] = {
        n["name"].lower().strip(): n["id"] for n in existing_nodes
    }
    existing_edge_set: set[tuple[str, str, str]] = {
        (e.get("source_id", ""), e.get("target_id", ""), e.get("relation_type", ""))
        for e in existing_edges
    }

    # ── Nodes ────────────────────────────────────────────────
    node_results: list[NodeDedupResult] = []
    for node in extracted_nodes:
        key = node.name.lower().strip()
        if key in existing_by_name:
            node_results.append(NodeDedupResult(
                name=node.name,
                type=node.type,
                status="exact_duplicate",
                decision="skip",
                matched_node_id=existing_by_name[key],
            ))
        else:
            node_results.append(NodeDedupResult(
                name=node.name,
                type=node.type,
                status="new",
                decision="add",
            ))

    # ── Edges ────────────────────────────────────────────────
    # Names resolvable from existing KG + nodes being added this run
    new_node_names = {r.name.lower().strip() for r in node_results if r.decision == "add"}
    all_known_names = set(existing_by_name.keys()) | new_node_names

    edge_results: list[EdgeDedupResult] = []
    for edge in extracted_edges:
        src_key = edge.source_name.lower().strip()
        tgt_key = edge.target_name.lower().strip()

        # Drop edges whose endpoints are neither in KG nor being added
        if src_key not in all_known_names or tgt_key not in all_known_names:
            edge_results.append(EdgeDedupResult(
                source_name=edge.source_name,
                target_name=edge.target_name,
                relation=edge.relation,
                status="exact_duplicate",
                decision="skip",
            ))
            continue

        # Check exact duplicate when both endpoints exist in KG
        src_id = existing_by_name.get(src_key)
        tgt_id = existing_by_name.get(tgt_key)
        if src_id and tgt_id and (src_id, tgt_id, edge.relation) in existing_edge_set:
            edge_results.append(EdgeDedupResult(
                source_name=edge.source_name,
                target_name=edge.target_name,
                relation=edge.relation,
                status="exact_duplicate",
                decision="skip",
            ))
            continue

        edge_results.append(EdgeDedupResult(
            source_name=edge.source_name,
            target_name=edge.target_name,
            relation=edge.relation,
            status="new",
            decision="add",
        ))

    return DedupReport(nodes=node_results, edges=edge_results)
