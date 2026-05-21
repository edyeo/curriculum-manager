"""
Neo4j constraint/index 적용 스크립트 (migration pipeline과 별개).

Usage:
  python schema/apply_schema.py
  python schema/apply_schema.py --neo4j-uri bolt://localhost:7687 --user neo4j --password curriculum_password
"""
import argparse
from pathlib import Path

from neo4j import GraphDatabase


def apply_schema(uri: str, user: str, password: str) -> None:
    schema_file = Path(__file__).parent / "schema.cypher"
    # 각 statement에서 주석 줄 제거 후 빈 statement 스킵
    raw_statements = schema_file.read_text().split(";")
    statements = []
    for s in raw_statements:
        lines = [ln for ln in s.splitlines() if not ln.strip().startswith("//")]
        stmt = "\n".join(lines).strip()
        if stmt:
            statements.append(stmt)

    driver = GraphDatabase.driver(uri, auth=(user, password))
    try:
        with driver.session() as session:
            for stmt in statements:
                if not stmt:
                    continue
                session.run(stmt)
                print(f"  OK: {stmt[:80].replace(chr(10), ' ')}")
    finally:
        driver.close()


def main() -> None:
    parser = argparse.ArgumentParser(description="Neo4j constraint/index 적용")
    parser.add_argument("--neo4j-uri", default="bolt://localhost:7687")
    parser.add_argument("--user", default="neo4j")
    parser.add_argument("--password", default="curriculum_password")
    args = parser.parse_args()

    print(f"Connecting to {args.neo4j_uri} ...")
    apply_schema(args.neo4j_uri, args.user, args.password)
    print("Schema applied.")


if __name__ == "__main__":
    main()
