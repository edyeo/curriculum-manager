"""
PassIterationHarness: 세 트리거의 진입점 디스패처
"""
from shared.schemas import EntityType, GraphState, Edge, RelationType
from shared.state_manager import load_nodes, load_edges, save_nodes, save_edges, load_state, snapshot_work
from agents.curriculum_manager.src.graphs.draft_graph import build_draft_graph
from agents.curriculum_manager.src.graphs.link_graph import build_link_graph
from agents.curriculum_manager.src.graphs.expand_graph import build_expand_graph


class PassIterationHarness:
    def __init__(self):
        self.nodes = load_nodes()
        self.edges = load_edges()

    def trigger_draft(self, subject: str) -> None:
        """Phase 1: 세 에이전트가 병렬로 노드 초안 생성 → nodes.json 저장"""
        print(f"\n🚀 [T1 DRAFT] 주제: '{subject}'")
        graph = build_draft_graph()
        result = graph.invoke({"subject": subject, "nodes": []})

        self.nodes = result["nodes"]
        self.edges = []

        # parent_name 기반 has_subtopic edge 자동 생성
        name_to_id = {n.name: n.id for n in self.nodes}
        for node in self.nodes:
            parent_name = node.metadata.pop("_parent_name", None)
            if parent_name and parent_name in name_to_id:
                self.edges.append(Edge(
                    source_id=name_to_id[parent_name],
                    target_id=node.id,
                    relation_type=RelationType("has_subtopic"),
                    logic_basis=f"{parent_name} has {node.name} as a subtopic.",
                    created_by_trigger="T1_DRAFT",
                ))

        save_nodes(self.nodes)
        save_edges(self.edges)
        snapshot_work(self.nodes, self.edges, trigger="T1_DRAFT", subject=subject)

        print(f"✅ DRAFT 완료: 총 {len(self.nodes)}개 노드, {len(self.edges)}개 has_subtopic edge")

    def trigger_link(self, source_type: str, target_type: str) -> None:
        """Phase 2: 지정된 두 타입 간 Pairwise 엣지 생성 → edges.json 저장"""
        print(f"\n🔗 [T2 LINK] {source_type} → {target_type}")

        src_enum = EntityType(source_type)
        tgt_enum = EntityType(target_type)

        source_nodes = [n for n in self.nodes if n.type == src_enum]
        target_nodes = [n for n in self.nodes if n.type == tgt_enum]

        if not source_nodes:
            print(f"⚠️  {source_type} 노드가 없습니다. DRAFT를 먼저 실행하세요.")
            return
        if not target_nodes:
            print(f"⚠️  {target_type} 노드가 없습니다. DRAFT를 먼저 실행하세요.")
            return

        print(f"  Source({source_type}): {len(source_nodes)}개 / Target({target_type}): {len(target_nodes)}개")

        graph = build_link_graph()
        result = graph.invoke(
            {
                "source_type": source_type,
                "target_type": target_type,
                "source_nodes": source_nodes,
                "target_nodes": target_nodes,
                "new_edges": [],
            }
        )

        self.edges.extend(result["new_edges"])
        save_edges(self.edges)   # edges.json만 업데이트
        snapshot_work(
            self.nodes, self.edges,
            trigger=f"T2_LINK_{source_type}_{target_type}",
        )

        print(f"✅ LINK 완료: {len(result['new_edges'])}개 엣지 추가 (총 {len(self.edges)}개)")

    def trigger_link_ai(
        self,
        source_type: str | None = None,
        source_depth: int | None = None,
        target_type: str | None = None,
        target_depth: int | None = None,
        edge_type: str | None = None,
        source_node_id: str | None = None,
    ) -> list[Edge]:
        """AI Link: 사용자 지정 조건으로 엣지 생성"""
        print(f"\n🔗 [AI LINK] source={source_node_id or f'{source_type}(D{source_depth})'} → {target_type}(D{target_depth}) [{edge_type}]")

        if source_node_id:
            source_nodes = [n for n in self.nodes if n.id == source_node_id]
            if not source_nodes:
                print(f"⚠️  source_node_id '{source_node_id}' 를 찾을 수 없습니다.")
                return []
        else:
            source_nodes = [
                n for n in self.nodes
                if (source_type is None or n.type.value == source_type)
                and (source_depth is None or n.depth == source_depth)
            ]

        target_nodes = [
            n for n in self.nodes
            if (target_type is None or n.type.value == target_type)
            and (target_depth is None or n.depth == target_depth)
        ]

        if not source_nodes:
            print("⚠️  source 조건에 맞는 노드가 없습니다.")
            return []
        if not target_nodes:
            print("⚠️  target 조건에 맞는 노드가 없습니다.")
            return []

        print(f"  Source: {len(source_nodes)}개 / Target: {len(target_nodes)}개")

        graph = build_link_graph()
        result = graph.invoke({
            "source_type": source_type or "custom",
            "target_type": target_type or "custom",
            "source_nodes": source_nodes,
            "target_nodes": target_nodes,
            "new_edges": [],
            "edge_type_constraint": edge_type,
        })

        existing_pairs = {(e.source_id, e.target_id) for e in self.edges}
        new_edges = [
            e for e in result["new_edges"]
            if (e.source_id, e.target_id) not in existing_pairs
        ]

        self.edges.extend(new_edges)
        save_edges(self.edges)
        snapshot_work(self.nodes, self.edges, trigger="AI_LINK")

        print(f"✅ AI LINK 완료: {len(new_edges)}개 엣지 추가 (총 {len(self.edges)}개)")
        return new_edges

    def trigger_link_ai_preview(
        self,
        source_type: str | None = None,
        source_depth: int | None = None,
        target_type: str | None = None,
        target_depth: int | None = None,
        edge_type: str | None = None,
        source_node_id: str | None = None,
    ) -> list[Edge]:
        """AI Link 미리보기: 저장 없이 후보 엣지 목록만 반환"""
        print(f"\n🔍 [AI LINK PREVIEW] source={source_node_id or f'{source_type}(D{source_depth})'} → {target_type}(D{target_depth}) [{edge_type}]")

        if source_node_id:
            source_nodes = [n for n in self.nodes if n.id == source_node_id]
            if not source_nodes:
                return []
        else:
            source_nodes = [
                n for n in self.nodes
                if (source_type is None or n.type.value == source_type)
                and (source_depth is None or n.depth == source_depth)
            ]

        target_nodes = [
            n for n in self.nodes
            if (target_type is None or n.type.value == target_type)
            and (target_depth is None or n.depth == target_depth)
        ]

        if not source_nodes or not target_nodes:
            return []

        graph = build_link_graph()
        result = graph.invoke({
            "source_type": source_type or "custom",
            "target_type": target_type or "custom",
            "source_nodes": source_nodes,
            "target_nodes": target_nodes,
            "new_edges": [],
            "edge_type_constraint": edge_type,
        })

        existing_pairs = {(e.source_id, e.target_id) for e in self.edges}
        new_edges = [
            e for e in result["new_edges"]
            if (e.source_id, e.target_id) not in existing_pairs
        ]

        print(f"✅ AI LINK PREVIEW 완료: {len(new_edges)}개 후보 엣지 (저장 안 함)")
        return new_edges

    def trigger_expand(self) -> None:
        """Phase 3: TechStack 역방향 추론으로 새 Seed 생성 → nodes.json + edges.json 저장"""
        print("\n🌱 [T3 EXPAND] 그래프 진화 확장")

        if not self.nodes:
            print("⚠️  노드가 없습니다. DRAFT를 먼저 실행하세요.")
            return

        import datetime
        import os
        
        os.makedirs("logs", exist_ok=True)
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        log_file_path = f"logs/expand_debate_{timestamp}.log"
        print(f"  [Log] 토론 과정이 {log_file_path} 에 저장됩니다.")

        graph = build_expand_graph()
        result = graph.invoke(
            {
                "existing_nodes": self.nodes,
                "existing_edges": self.edges,
                "new_nodes": [],
                "new_edges": [],
                "log_file_path": log_file_path,
            }
        )

        self.nodes.extend(result["new_nodes"])
        self.edges.extend(result["new_edges"])

        save_nodes(self.nodes)   # 새 Seed 노드 포함
        save_edges(self.edges)   # 새 엣지 포함
        snapshot_work(self.nodes, self.edges, trigger="T3_EXPAND")

        print(
            f"✅ EXPAND 완료: 새 Seed {len(result['new_nodes'])}개, "
            f"새 엣지 {len(result['new_edges'])}개 추가"
        )

    def show(self) -> None:
        """현재 nodes.json + edges.json 요약 출력"""
        nodes = load_nodes()
        edges = load_edges()

        print("\n📊 [STATE 요약]")
        print(f"  총 노드: {len(nodes)}개  (nodes.json)")

        for etype in EntityType:
            ns = [n for n in nodes if n.type == etype]
            depths = {}
            for n in ns:
                depths.setdefault(n.depth, []).append(n)
            depth_info = ", ".join(f"D{d}={len(v)}" for d, v in sorted(depths.items()))
            print(f"    {etype.value:12s}: {len(ns):3d}개  [{depth_info}]")

        print(f"\n  총 엣지: {len(edges)}개  (edges.json)")
        if edges:
            from collections import Counter
            rel_count = Counter(e.relation_type for e in edges)
            for rel, cnt in rel_count.items():
                print(f"    {rel:20s}: {cnt}개")

        # 정합성 검사
        node_depth = {n.id: n.depth for n in nodes}
        bad_edges = [
            e for e in edges
            if node_depth.get(e.source_id) != node_depth.get(e.target_id)
        ]
        if bad_edges:
            print(f"\n  ⚠️  depth 불일치 엣지: {len(bad_edges)}개 (정합성 위반)")
        else:
            print(f"\n  ✅ 정합성 검증 통과 (모든 엣지가 동일 depth 간 연결)")

        # 진화성 검사
        expanded_seeds = [n for n in nodes if n.type == EntityType.Seed and n.depth == 3]
        print(f"  {'✅' if expanded_seeds else '⬜'} EXPAND Seed(D3): {len(expanded_seeds)}개")
