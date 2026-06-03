"""KG Refiner Harness — T_STRUCTURE / T_STUDENT 트리거 디스패처."""
from agents.kg_refiner.src.graphs.structure_graph import build_structure_graph
from agents.kg_refiner.src.graphs.student_graph import build_student_graph


class KGRefinerHarness:
    def trigger_structure(
        self,
        subject_id: str,
        node_types: list[str] | None = None,
        depth: int | None = None,
        root_node_id: str | None = None,
    ) -> str:
        """T_STRUCTURE: 서브그래프 추출 → 구조 검토 → 개선 제안."""
        print(f"\n[T_STRUCTURE] subject={subject_id}")
        graph = build_structure_graph()
        result = graph.invoke({
            "subject_id": subject_id,
            "node_types": node_types,
            "depth": depth,
            "root_node_id": root_node_id,
            "subgraph": {},
            "proposals": [],
            "validated_proposals": [],
            "output_path": "",
        })
        return result["output_path"]

    def trigger_student(
        self,
        subject_id: str,
        top_k: int = 50,
        min_students: int = 10,
        min_successors: int = 3,
    ) -> str:
        """T_STUDENT: 이상 노드 탐지 → 원인 조사 → 재설계 제안."""
        print(f"\n[T_STUDENT] subject={subject_id}  top_k={top_k}")
        graph = build_student_graph()
        result = graph.invoke({
            "subject_id": subject_id,
            "top_k": top_k,
            "min_students": min_students,
            "min_successors": min_successors,
            "anomalies": [],
            "proposals": [],
            "validated_proposals": [],
            "output_path": "",
        })
        return result["output_path"]
