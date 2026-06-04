#!/usr/bin/env python3
"""
KG Refiner CLI

사용법:
  python cli.py refine      --subject-id <id>
  python cli.py refine-node --subject-id <id> --node-id <node>
"""
import argparse
import sys
from dotenv import load_dotenv

load_dotenv()


def main():
    parser = argparse.ArgumentParser(
        prog="kg-refiner",
        description="KG Refiner: 이상 노드 검출 → 서브그래프 → 재정의 제안",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
예시:
  python cli.py refine      --subject-id abc123
  python cli.py refine      --subject-id abc123 --top-k 20 --min-successors 2 --depth 2
  python cli.py refine-node --subject-id abc123 --node-id n-001 --detection anomaly
        """,
    )

    subparsers = parser.add_subparsers(dest="command", metavar="COMMAND")

    # refine — 자체 검출 + 서브그래프 + 재정의 제안
    rf = subparsers.add_parser("refine", help="검출→서브그래프→재정의 제안")
    rf.add_argument("--subject-id", required=True, help="대상 Subject ID")
    rf.add_argument("--top-k", type=int, default=50, help="검출 이상 노드 상위 K개 (기본: 50)")
    rf.add_argument("--min-students", type=int, default=10, help="최소 샘플 학생 수 (기본: 10)")
    rf.add_argument("--min-successors", type=int, default=3, help="최소 후행 노드 수 (기본: 3)")
    rf.add_argument("--depth", type=int, default=1, help="검출 노드 기준 서브그래프 깊이 (기본: 1)")

    # refine-node — 외부 검출 노드 하나를 받아 재정의 제안
    rn = subparsers.add_parser("refine-node", help="외부 검출 노드 하나 재정의")
    rn.add_argument("--subject-id", required=True, help="대상 Subject ID")
    rn.add_argument("--node-id", required=True, help="외부에서 검출된 대상 노드 ID")
    rn.add_argument("--name", default="", help="노드 이름 (선택)")
    rn.add_argument("--detection", default="external", help="검출 근거 (anomaly|degenerate|external)")
    rn.add_argument("--depth", type=int, default=1, help="노드 기준 서브그래프 깊이 (기본: 1)")

    args = parser.parse_args()

    if args.command is None:
        parser.print_help()
        sys.exit(0)

    from agents.kg_refiner.src.harness import KGRefinerHarness
    harness = KGRefinerHarness()

    if args.command == "refine":
        result = harness.trigger_refine(
            subject_id=args.subject_id,
            top_k=args.top_k,
            min_students=args.min_students,
            min_successors=args.min_successors,
            depth=args.depth,
        )
        print(f"\n✅ 완료: 제안 {result['proposal_count']}개 → {result['output_path']}")

    elif args.command == "refine-node":
        result = harness.trigger_refine_node(
            subject_id=args.subject_id,
            node_id=args.node_id,
            name=args.name,
            detection=args.detection,
            depth=args.depth,
        )
        print(f"\n✅ 완료: 제안 {result['proposal_count']}개 → {result['output_path']}")


if __name__ == "__main__":
    main()
