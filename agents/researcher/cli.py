#!/usr/bin/env python3
"""
Researcher CLI
사용법:
  python cli.py research <entity_id>
  python cli.py query --entity-id <entity_id>
  python cli.py summary <entity_id>
  python cli.py show <entity_id>
"""
import argparse
import sys
from dotenv import load_dotenv

load_dotenv()


def main():
    parser = argparse.ArgumentParser(
        prog="researcher",
        description="Researcher: Entity 강화를 위한 자동 조사 에이전트",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
예시:
  python cli.py research abc123
  python cli.py query --entity-id abc123 --keyword "distributed"
  python cli.py summary abc123
  python cli.py show abc123
        """,
    )

    subparsers = parser.add_subparsers(dest="command", metavar="COMMAND")

    # research
    research_p = subparsers.add_parser("research", help="Entity 조사 시작 (RESEARCH)")
    research_p.add_argument("entity_id", help="조사할 Entity ID")

    # query
    query_p = subparsers.add_parser("query", help="조사 결과 조회")
    query_p.add_argument(
        "--entity-id",
        help="Entity ID 필터",
    )
    query_p.add_argument(
        "--keyword",
        help="키워드 필터",
    )
    query_p.add_argument(
        "--source",
        help="출처 필터 (web_search, blog, github 등)",
    )
    query_p.add_argument(
        "--limit",
        type=int,
        default=20,
        help="최대 결과 수 (기본: 20)",
    )

    # summary
    summary_p = subparsers.add_parser("summary", help="조사 요약 조회")
    summary_p.add_argument("entity_id", help="Entity ID")

    # show
    show_p = subparsers.add_parser("show", help="Entity 조사 결과 표시")
    show_p.add_argument("entity_id", help="Entity ID")

    args = parser.parse_args()

    if args.command is None:
        parser.print_help()
        sys.exit(0)

    from agents.researcher.src.harness import ResearcherHarness
    harness = ResearcherHarness()

    if args.command == "research":
        harness.trigger_research(args.entity_id)
    elif args.command == "query":
        result = harness.query_results(
            entity_id=args.entity_id,
            keyword=args.keyword,
            source=args.source,
            limit=args.limit
        )
        print(f"\n📋 조회 결과: {result['results_count']}개")
        for res in result.get("results", []):
            print(f"\n  [{res.get('keyword')}]")
            print(f"    제목: {res.get('title')}")
            print(f"    요약: {res.get('summary', '')[:100]}...")
    elif args.command == "summary":
        summary = harness.get_summary(args.entity_id)
        print(f"\n📊 조사 요약:")
        print(f"  총 결과: {summary.get('total_results', 0)}개")
        print(f"  키워드: {summary.get('keyword_count', 0)}개")
        print(f"  마지막 업데이트: {summary.get('last_updated', 'N/A')}")
    elif args.command == "show":
        harness.show_entity_research(args.entity_id)


if __name__ == "__main__":
    main()
