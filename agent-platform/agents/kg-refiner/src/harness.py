"""KG Refiner Harness — REFINE 트리거 디스패처.

- trigger_refine      : 자체 검출(node-resolution) → 검출 노드 중심 서브그래프 → 재정의 제안
- trigger_refine_node : 외부 pipeline이 검출한 노드 하나를 받아 (검출 스킵) 재정의 제안
"""
from agents.kg_refiner.src.graphs.structure_graph import build_structure_graph


class KGRefinerHarness:
    def trigger_refine(
        self,
        subject_id: str,
        top_k: int = 50,
        min_students: int = 10,
        min_successors: int = 3,
        depth: int = 1,
    ) -> dict:
        """REFINE: 이상 노드 검출 → 검출 노드 중심 서브그래프 → 재정의 제안.

        Returns: {trigger, subject_id, detected_count, proposal_count,
                  proposals, output_path}
        """
        print(f"\n[REFINE] subject={subject_id}  top_k={top_k} depth={depth}")
        graph = build_structure_graph()
        result = graph.invoke({
            "subject_id": subject_id,
            "top_k": top_k,
            "min_students": min_students,
            "min_successors": min_successors,
            "depth": depth,
            "detected_nodes": [],
            "subgraphs": {},
            "proposals": [],
            "validated_proposals": [],
            "output_path": "",
        })
        return {
            "trigger": "REFINE",
            "subject_id": subject_id,
            "detected_count": len(result.get("detected_nodes", [])),
            "proposal_count": len(result.get("validated_proposals", [])),
            "proposals": result.get("validated_proposals", []),
            "output_path": result.get("output_path", ""),
        }

    def trigger_refine_node(
        self,
        subject_id: str,
        node_id: str,
        name: str = "",
        detection: str = "external",
        info: dict | None = None,
        depth: int = 1,
    ) -> dict:
        """단일 노드 재정의: 외부 pipeline이 검출한 노드 하나를 받아
        해당 노드 중심 서브그래프 도출 → 재정의 제안.

        검출 단계(detect_targets)를 건너뛰고 detected_nodes를 직접 주입한다.

        Args:
            node_id: 외부에서 검출된 대상 노드 ID
            name: 노드 이름 (생략 시 서브그래프에서 확인)
            detection: 검출 근거 유형 (anomaly|degenerate|external)
            info: 외부 검출 메트릭 (점수·사유 등, propose 컨텍스트로 활용)

        Returns: {trigger, subject_id, node_id, proposal_count, proposals, output_path}
        """
        print(f"\n[REFINE_NODE] subject={subject_id} node={node_id} detection={detection}")
        graph = build_structure_graph()
        result = graph.invoke({
            "subject_id": subject_id,
            "top_k": 0,
            "min_students": 0,
            "min_successors": 0,
            "depth": depth,
            "detected_nodes": [{
                "node_id": node_id,
                "name": name,
                "detection": detection,
                "info": info or {},
            }],
            "subgraphs": {},
            "proposals": [],
            "validated_proposals": [],
            "output_path": "",
        })
        return {
            "trigger": "REFINE_NODE",
            "subject_id": subject_id,
            "node_id": node_id,
            "proposal_count": len(result.get("validated_proposals", [])),
            "proposals": result.get("validated_proposals", []),
            "output_path": result.get("output_path", ""),
        }
