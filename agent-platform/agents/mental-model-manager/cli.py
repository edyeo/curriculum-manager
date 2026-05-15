#!/usr/bin/env python3
"""
Mental Model Manager CLI
사용법:
  python cli.py generate <entity_id>
  python cli.py rubric <entity_id> [--level junior|senior|staff]
  python cli.py count <entity_id>
"""
import argparse
import sys
from dotenv import load_dotenv

load_dotenv()


def main():
    parser = argparse.ArgumentParser(
        prog="mental-model-manager",
        description="Mental Model Manager: Entity별 평가 기준(Rubric) 생성",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
예시:
  python cli.py generate abc123
  python cli.py rubric abc123
  python cli.py rubric abc123 --level senior
  python cli.py count abc123
        """,
    )

    subparsers = parser.add_subparsers(dest="command", metavar="COMMAND")

    # generate
    generate_p = subparsers.add_parser("generate", help="Mental Model 평가 기준 생성")
    generate_p.add_argument("entity_id", help="평가 기준을 생성할 Entity ID")

    # rubric
    rubric_p = subparsers.add_parser("rubric", help="Mental Model 평가 기준 조회")
    rubric_p.add_argument("entity_id", help="Entity ID")
    rubric_p.add_argument(
        "--level",
        choices=["junior", "senior", "staff"],
        help="특정 수준만 표시 (기본: 모두)",
    )

    # count
    count_p = subparsers.add_parser("count", help="평가 항목 개수 조회")
    count_p.add_argument("entity_id", help="Entity ID")

    args = parser.parse_args()

    if args.command is None:
        parser.print_help()
        sys.exit(0)

    from agents.mental_model_manager.src.harness import MentalModelManagerHarness
    harness = MentalModelManagerHarness()

    if args.command == "generate":
        harness.trigger_generate(args.entity_id)
    elif args.command == "rubric":
        harness.show_rubric(args.entity_id, level=args.level)
    elif args.command == "count":
        counts = harness.get_level_count(args.entity_id)
        if "error" in counts:
            print(f"\n❌ {counts['error']}")
        else:
            print(f"\n📊 평가 항목 개수")
            print(f"  Entity: {counts['entity_name']}")
            print(f"  주니어: {counts['junior_count']}개")
            print(f"  시니어: {counts['senior_count']}개")
            print(f"  스태프: {counts['staff_count']}개")
            print(f"  총합: {counts['junior_count'] + counts['senior_count'] + counts['staff_count']}개")


if __name__ == "__main__":
    main()
