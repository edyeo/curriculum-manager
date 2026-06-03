#!/usr/bin/env python3
"""
KG Refiner CLI

사용법:
  python cli.py structure --subject-id <id>
  python cli.py student   --subject-id <id> --top-k 30
"""
import argparse
import sys
from dotenv import load_dotenv

load_dotenv()


def main():
    parser = argparse.ArgumentParser(
        prog="kg-refiner",
        description="KG Refiner: 지식 그래프 구조 검토 및 이상 노드 탐지",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
예시:
  python cli.py structure --subject-id abc123
  python cli.py structure --subject-id abc123 --node-types Concept,Seed --depth 2
  python cli.py student   --subject-id abc123
  python cli.py student   --subject-id abc123 --top-k 30 --min-students 5
        """,
    )

    subparsers = parser.add_subparsers(dest="command", metavar="COMMAND")

    # structure
    sp = subparsers.add_parser("structure", help="T_STRUCTURE: 서브그래프 구조 검토")
    sp.add_argument("--subject-id", required=True, help="대상 Subject ID")
    sp.add_argument("--node-types", help="콤마 구분 노드 타입 필터 (예: Seed,Concept)")
    sp.add_argument("--depth", type=int, help="서브그래프 탐색 깊이")
    sp.add_argument("--root-node-id", help="특정 노드 중심 서브그래프")

    # student
    st = subparsers.add_parser("student", help="T_STUDENT: 학생 데이터 기반 이상 노드 탐지")
    st.add_argument("--subject-id", required=True, help="대상 Subject ID")
    st.add_argument("--top-k", type=int, default=50, help="이상 노드 상위 K개 (기본: 50)")
    st.add_argument("--min-students", type=int, default=10, help="최소 샘플 학생 수 (기본: 10)")
    st.add_argument("--min-successors", type=int, default=3, help="최소 후행 노드 수 (기본: 3)")

    args = parser.parse_args()

    if args.command is None:
        parser.print_help()
        sys.exit(0)

    from agents.kg_refiner.src.harness import KGRefinerHarness
    harness = KGRefinerHarness()

    if args.command == "structure":
        node_types = [t.strip() for t in args.node_types.split(",")] if args.node_types else None
        output = harness.trigger_structure(
            subject_id=args.subject_id,
            node_types=node_types,
            depth=args.depth,
            root_node_id=args.root_node_id,
        )
        print(f"\n✅ 완료: {output}")

    elif args.command == "student":
        output = harness.trigger_student(
            subject_id=args.subject_id,
            top_k=args.top_k,
            min_students=args.min_students,
            min_successors=args.min_successors,
        )
        print(f"\n✅ 완료: {output}")


if __name__ == "__main__":
    main()
