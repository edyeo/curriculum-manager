#!/usr/bin/env python3
"""
Question Generator CLI
사용법:
  python cli.py generate <entity_id>
  python cli.py query --entity-id <entity_id> [--difficulty easy|medium|hard]
  python cli.py stats <entity_id>
  python cli.py show <entity_id>
"""
import argparse
import sys
from dotenv import load_dotenv

load_dotenv()


def main():
    parser = argparse.ArgumentParser(
        prog="question-generator",
        description="Question Generator: Entity 기반 자동 문제 생성",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
예시:
  python cli.py generate abc123
  python cli.py query --entity-id abc123 --difficulty medium
  python cli.py stats abc123
  python cli.py show abc123
        """,
    )

    subparsers = parser.add_subparsers(dest="command", metavar="COMMAND")

    # generate
    generate_p = subparsers.add_parser("generate", help="Entity에 대한 문제 생성 (GENERATE)")
    generate_p.add_argument("entity_id", help="문제를 생성할 Entity ID")

    # query
    query_p = subparsers.add_parser("query", help="문제 조회")
    query_p.add_argument(
        "--entity-id",
        help="Entity ID 필터",
    )
    query_p.add_argument(
        "--difficulty",
        choices=["easy", "medium", "hard"],
        help="난이도 필터",
    )
    query_p.add_argument(
        "--limit",
        type=int,
        default=20,
        help="최대 결과 수 (기본: 20)",
    )

    # stats
    stats_p = subparsers.add_parser("stats", help="문제 통계 조회")
    stats_p.add_argument("entity_id", help="Entity ID")

    # show
    show_p = subparsers.add_parser("show", help="Entity 문제 통계 표시")
    show_p.add_argument("entity_id", help="Entity ID")

    args = parser.parse_args()

    if args.command is None:
        parser.print_help()
        sys.exit(0)

    from agents.question_generator.src.harness import QuestionGeneratorHarness
    harness = QuestionGeneratorHarness()

    if args.command == "generate":
        harness.trigger_generate(args.entity_id)
    elif args.command == "query":
        result = harness.query_questions(
            entity_id=args.entity_id,
            difficulty_level=args.difficulty,
            limit=args.limit
        )
        print(f"\n📋 조회 결과: {result['count']}개")
        for i, q in enumerate(result.get("questions", [])[:5], 1):
            print(f"\n  [{i}] {q.get('difficulty_level', 'medium').upper()}")
            print(f"      {q.get('question_text', '')[:80]}...")
    elif args.command == "stats":
        stats = harness.get_statistics(args.entity_id)
        print(f"\n📊 문제 통계:")
        print(f"  총 문제: {stats.get('total_questions', 0)}개")
        if stats.get('total_questions', 0) > 0:
            print(f"  쉬움: {stats.get('easy_count', 0)}개")
            print(f"  중간: {stats.get('medium_count', 0)}개")
            print(f"  어려움: {stats.get('hard_count', 0)}개")
    elif args.command == "show":
        harness.show_statistics(args.entity_id)


if __name__ == "__main__":
    main()
