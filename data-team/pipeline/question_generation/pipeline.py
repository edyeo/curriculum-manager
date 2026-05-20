"""
문제 생성 파이프라인
Usage: python pipeline.py [--config config.yaml] [--dry-run]
"""
import argparse
import sys
import time
from collections import defaultdict
from pathlib import Path

import httpx
import yaml


def load_config(path: str) -> dict:
    with open(path) as f:
        return yaml.safe_load(f)


# ── Step 1: 인증 ──────────────────────────────────────────────────────────────

def authenticate(client: httpx.Client, cfg: dict) -> str:
    resp = client.post("/api/auth/login", json={
        "email": cfg["api"]["email"],
        "password": cfg["api"]["password"],
    })
    resp.raise_for_status()
    token = resp.json()["access_token"]
    print(f"[1/4] 인증 완료")
    return token


# ── Step 2: Subject 조회 ───────────────────────────────────────────────────────

def get_subject(client: httpx.Client, subject_id: str) -> dict:
    resp = client.get(f"/api/subjects/{subject_id}")
    resp.raise_for_status()
    subject = resp.json()
    print(f"[2/4] Subject: {subject['name']} ({subject['id']})")
    return subject


# ── Step 3: 분포도 조회 및 강화 대상 선정 ─────────────────────────────────────

def analyze_and_select_targets(
    client: httpx.Client,
    subject: dict,
    cfg: dict,
) -> list[dict]:
    """
    지정된 subject의 (node, question_type) 중
    published 문제 수 < min_questions 인 조합을 반환.
    """
    min_q = cfg["min_questions"]
    question_types = cfg["question_types"]
    max_targets = cfg["generation"]["max_targets"]

    print(f"[3/4] 분포도 조회 중...")

    nodes_resp = client.get(f"/api/subjects/{subject['id']}/nodes")
    nodes_resp.raise_for_status()
    nodes = nodes_resp.json().get("nodes", [])

    all_q_resp = client.get("/api/question-workbench/questions", params={"status": "published"})
    all_q_resp.raise_for_status()
    questions = all_q_resp.json().get("questions", [])

    # (entity_id, question_type) → count
    counts: dict[tuple, int] = defaultdict(int)
    for q in questions:
        counts[(q["entity_id"], q["question_type"])] += 1

    targets = []
    for node in nodes:
        for qtype in question_types:
            current = counts[(node["id"], qtype)]
            if current < min_q:
                targets.append({
                    "subject_id": subject["id"],
                    "subject_name": subject["name"],
                    "node_id": node["id"],
                    "node_name": node["name"],
                    "question_type": qtype,
                    "current_count": current,
                    "gap": min_q - current,
                })

    targets.sort(key=lambda x: x["gap"], reverse=True)
    targets = targets[:max_targets]

    print(f"[3/4] 강화 대상 (node × type): {len(targets)}개  (min={min_q}, types={question_types})")
    for t in targets:
        print(f"       - [{t['question_type']}] {t['node_name'][:40]} | 현재 {t['current_count']}개 (부족 {t['gap']}개)")

    return targets


# ── Step 4: 문제 생성 요청 ────────────────────────────────────────────────────

def generate_questions(client: httpx.Client, targets: list[dict], cfg: dict) -> dict:
    blueprint_id = cfg["generation"]["blueprint_id"]
    count_per_target = cfg["generation"].get("count_per_target", 3)
    max_questions = cfg["generation"].get("max_questions")  # None = 무제한
    poll_interval = cfg["generation"]["poll_interval"]
    poll_timeout = cfg["generation"]["poll_timeout"]

    results = {"success": 0, "failed": 0, "skipped": 0, "total_generated": 0}

    cap_info = f", 전체 상한 {max_questions}개" if max_questions else ""
    print(f"[4/4] 문제 생성 시작 ({len(targets)}개 조합{cap_info})")

    for i, target in enumerate(targets, 1):
        if max_questions and results["total_generated"] >= max_questions:
            print(f"  → 전체 상한 {max_questions}개 도달, 나머지 {len(targets) - i + 1}개 조합 스킵")
            break

        label = f"[{target['question_type']}] {target['node_name'][:35]}"
        print(f"  ({i}/{len(targets)}) {label} ...", end=" ", flush=True)

        # 생성 요청
        payload = {
            "entity_id": target["node_id"],
            "question_type": target["question_type"],
            "count": count_per_target,
        }
        if blueprint_id:
            payload["blueprint_id"] = blueprint_id

        resp = client.post("/api/question-workbench/generate", json=payload)
        if resp.status_code not in (200, 201, 202):
            print(f"요청 실패 ({resp.status_code})")
            results["failed"] += 1
            continue

        job_id = resp.json()["job_id"]

        # job 완료 폴링
        deadline = time.time() + poll_timeout
        status = "pending"
        while time.time() < deadline:
            time.sleep(poll_interval)
            job_resp = client.get(f"/api/question-workbench/jobs/{job_id}")
            if job_resp.status_code != 200:
                break
            job = job_resp.json()
            status = job.get("status")
            if status in ("completed", "failed"):
                break

        if status == "completed":
            result = job.get("result") or []
            if isinstance(result, list):
                generated = len(result)
            elif isinstance(result, dict):
                generated = len(result.get("questions", []))
            else:
                generated = 0
            results["total_generated"] += generated
            print(f"완료 ({generated}개 생성, 누적 {results['total_generated']}개)")
            results["success"] += 1
        elif status == "failed":
            print(f"실패: {job.get('error', '')[:60]}")
            results["failed"] += 1
        else:
            print(f"타임아웃 (job_id={job_id})")
            results["skipped"] += 1

    return results


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="문제 생성 파이프라인")
    parser.add_argument("--subject-id", required=True, help="대상 subject ID")
    parser.add_argument("--config", default=str(Path(__file__).parent / "config.yaml"))
    parser.add_argument("--dry-run", action="store_true", help="대상 선정까지만 실행 (생성 안 함)")
    args = parser.parse_args()

    cfg = load_config(args.config)
    base_url = cfg["api"]["base_url"]

    with httpx.Client(base_url=base_url, timeout=30) as client:
        # Step 1
        token = authenticate(client, cfg)
        client.headers["Authorization"] = f"Bearer {token}"

        # Step 2
        subject = get_subject(client, args.subject_id)

        # Step 3
        targets = analyze_and_select_targets(client, subject, cfg)

        if not targets:
            print("강화 대상 없음 — 종료")
            return

        if args.dry_run:
            print("[dry-run] 생성 단계 스킵")
            return

        # Step 4
        results = generate_questions(client, targets, cfg)

    print()
    print("=" * 50)
    print(f"완료: 성공 {results['success']} / 실패 {results['failed']} / 타임아웃 {results['skipped']}  (총 {results['total_generated']}개 생성)")


if __name__ == "__main__":
    main()
