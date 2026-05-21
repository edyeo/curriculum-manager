"""
KG Neo4j 마이그레이션 파이프라인

Usage:
  python pipeline.py                              # 전체 실행
  python pipeline.py --subject-id <id>            # 특정 subject만
  python pipeline.py --dry-run                    # 카운트만 출력 (쓰기 없음)
  python pipeline.py --reset                      # Neo4j 초기화 후 재실행
  python pipeline.py --config path/to/config.yaml
"""
import argparse
from pathlib import Path

import yaml
from neo4j import GraphDatabase

import db as dbmod
import neo4j_writer as writer


def load_config(path: str) -> dict:
    with open(path) as f:
        return yaml.safe_load(f)


def main() -> None:
    parser = argparse.ArgumentParser(description="KG Neo4j 마이그레이션 파이프라인")
    parser.add_argument("--config", default=str(Path(__file__).parent / "config.yaml"))
    parser.add_argument("--subject-id", help="특정 subject만 마이그레이션")
    parser.add_argument("--dry-run", action="store_true", help="카운트만 출력 (쓰기 없음)")
    parser.add_argument("--reset", action="store_true", help="Neo4j 데이터 초기화 후 재실행")
    args = parser.parse_args()

    cfg = load_config(args.config)
    mig = cfg["migration"]
    subject_id = args.subject_id or mig.get("subject_id")
    batch_size = mig.get("batch_size", 500)
    node_types = mig.get("node_types", ["Seed", "Concept", "TechStack", "System"])

    cm_engine = dbmod.get_engine(cfg["databases"]["contents_manager"])
    neo4j_cfg = cfg["neo4j"]

    # ── Extract ───────────────────────────────────────────────────────────────
    print("[1/4] Subject 추출 중...")
    subjects = dbmod.fetch_subjects(cm_engine, subject_id)
    print(f"  → {len(subjects)}개")

    print("[2/4] KG 노드 추출 중...")
    nodes = dbmod.fetch_nodes(cm_engine, subject_id, node_types)
    print(f"  → {len(nodes)}개 ({', '.join(node_types)})")

    print("[3/4] KG 엣지 추출 중...")
    edges = dbmod.fetch_edges(cm_engine, subject_id)
    print(f"  → {len(edges)}개")

    questions: list[dict] = []
    if mig.get("include_questions", True):
        print("[4/4] 문제 추출 중...")
        questions = dbmod.fetch_questions(
            cm_engine, subject_id, mig.get("question_status", "published")
        )
        print(f"  → {len(questions)}개")

    if args.dry_run:
        print("\n[dry-run] 마이그레이션 예정:")
        print(f"  Subject: {len(subjects)}개")
        print(f"  KG 노드: {len(nodes)}개")
        print(f"  KG 엣지: {len(edges)}개")
        print(f"  Question: {len(questions)}개")
        return

    # ── Load ──────────────────────────────────────────────────────────────────
    driver = GraphDatabase.driver(
        neo4j_cfg["uri"], auth=(neo4j_cfg["user"], neo4j_cfg["password"])
    )
    try:
        if args.reset:
            print("\n[reset] Neo4j 데이터 초기화 중...")
            writer.reset_graph(driver)
            print("  → 완료")

        print("\n[Step 1] Subject 노드 MERGE...")
        cnt = writer.merge_subjects(driver, subjects)
        print(f"  → {cnt}개")

        print("[Step 2] KG 노드 MERGE...")
        cnt = writer.merge_nodes(driver, nodes, batch_size)
        print(f"  → {cnt}개")

        print("[Step 2b] CONTAINS 관계 MERGE...")
        cnt = writer.merge_contains(driver, nodes, batch_size)
        print(f"  → {cnt}개")

        print("[Step 3] KG 엣지 MERGE...")
        cnt = writer.merge_edges(driver, edges, batch_size)
        print(f"  → {cnt}개")

        if questions:
            print("[Step 4] Question 노드 MERGE + ABOUT 관계...")
            cnt = writer.merge_questions(driver, questions, batch_size)
            print(f"  → {cnt}개")

        print("\n" + "=" * 50)
        print(f"완료: Subject {len(subjects)}개 / 노드 {len(nodes)}개 / 엣지 {len(edges)}개 / 문제 {len(questions)}개")
    finally:
        driver.close()


if __name__ == "__main__":
    main()
