#!/usr/bin/env python3
"""
Pass-Iteration CLI
사용법:
  python cli.py draft "데이터 엔지니어링"
  python cli.py link --source Seed --target Concept
  python cli.py expand
  python cli.py show
"""
import argparse
import sys
from dotenv import load_dotenv

load_dotenv()


def main():
    parser = argparse.ArgumentParser(
        prog="cli",
        description="Pass-Iteration: 트리거 기반 커리큘럼 생성기",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
예시:
  python cli.py draft "데이터 엔지니어링"
  python cli.py link --source Seed --target Concept
  python cli.py link --source Concept --target TechStack
  python cli.py expand
  python cli.py show
        """,
    )

    subparsers = parser.add_subparsers(dest="command", metavar="COMMAND")

    # draft
    draft_p = subparsers.add_parser("draft", help="Phase 1: 노드 초안 생성 (DRAFT)")
    draft_p.add_argument("subject", help="생성할 주제 (예: '데이터 엔지니어링')")

    # link
    link_p = subparsers.add_parser("link", help="Phase 2: 노드 간 엣지 생성 (LINK)")
    link_p.add_argument(
        "--source",
        required=True,
        choices=["Seed", "Concept", "TechStack"],
        help="소스 엔터티 타입",
    )
    link_p.add_argument(
        "--target",
        required=True,
        choices=["Seed", "Concept", "TechStack"],
        help="타겟 엔터티 타입",
    )

    # expand
    subparsers.add_parser("expand", help="Phase 3: 그래프 진화 확장 (EXPAND)")

    # show
    subparsers.add_parser("show", help="현재 state.json 요약 출력")

    args = parser.parse_args()

    if args.command is None:
        parser.print_help()
        sys.exit(0)

    from src.harness import PassIterationHarness
    harness = PassIterationHarness()

    if args.command == "draft":
        harness.trigger_draft(args.subject)
    elif args.command == "link":
        harness.trigger_link(args.source, args.target)
    elif args.command == "expand":
        harness.trigger_expand()
    elif args.command == "show":
        harness.show()


if __name__ == "__main__":
    main()
