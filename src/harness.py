"""
PassIterationHarness: 세 트리거의 진입점 디스패처
"""
from src.schemas import EntityType, GraphState
from src.state_manager import load_nodes, load_edges, save_nodes, save_edges, load_state
from src.graphs.draft_graph import build_draft_graph
from src.graphs.link_graph import build_link_graph
from src.graphs.expand_graph import build_expand_graph


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
        self.edges = []          # DRAFT 시 엣지 초기화 (독립성 보장)

        save_nodes(self.nodes)
        save_edges(self.edges)   # edges.json도 빈 상태로 초기화

        print(f"✅ DRAFT 완료: 총 {len(self.nodes)}개 노드 (edges 초기화)")

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

        print(f"✅ LINK 완료: {len(result['new_edges'])}개 엣지 추가 (총 {len(self.edges)}개)")

    def trigger_expand(self) -> None:
        """Phase 3: TechStack 역방향 추론으로 새 Seed 생성 → nodes.json + edges.json 저장"""
        print("\n🌱 [T3 EXPAND] 그래프 진화 확장")

        if not self.nodes:
            print("⚠️  노드가 없습니다. DRAFT를 먼저 실행하세요.")
            return

        graph = build_expand_graph()
        result = graph.invoke(
            {
                "existing_nodes": self.nodes,
                "existing_edges": self.edges,
                "new_nodes": [],
                "new_edges": [],
            }
        )

        self.nodes.extend(result["new_nodes"])
        self.edges.extend(result["new_edges"])

        save_nodes(self.nodes)   # 새 Seed 노드 포함
        save_edges(self.edges)   # 새 엣지 포함

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
