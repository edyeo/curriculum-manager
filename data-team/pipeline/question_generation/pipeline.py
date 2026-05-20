"""
문제 생성 파이프라인
Usage:
  python pipeline.py --subject-id <id>            # 생성 + 파일 저장
  python pipeline.py --subject-id <id> --dry-run  # 대상 선정까지만
  python pipeline.py --load-and-save <file>       # 덤프 파일 → DB 저장
"""
import argparse
import json
import time
from collections import defaultdict
from datetime import datetime, timezone
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


# ── Step 4: 문제 생성 요청 → 파일 덤프 ───────────────────────────────────────

def generate_and_dump(
    client: httpx.Client,
    subject: dict,
    targets: list[dict],
    cfg: dict,
) -> Path:
    """
    각 타겟의 문제를 생성하고 결과를 output 디렉토리에 JSON 파일로 저장.
    저장된 파일 경로를 반환.
    """
    blueprint_id = cfg["generation"]["blueprint_id"]
    count_per_target = cfg["generation"].get("count_per_target", 3)
    max_questions = cfg["generation"].get("max_questions")
    poll_interval = cfg["generation"]["poll_interval"]
    poll_timeout = cfg["generation"]["poll_timeout"]

    output_dir = Path(__file__).parent / cfg.get("output_dir", "../../data/output")
    output_dir.mkdir(parents=True, exist_ok=True)

    stats = {"success": 0, "failed": 0, "skipped": 0, "total_generated": 0}
    all_questions: list[dict] = []

    cap_info = f", 전체 상한 {max_questions}개" if max_questions else ""
    print(f"[4/4] 문제 생성 시작 ({len(targets)}개 조합{cap_info})")

    for i, target in enumerate(targets, 1):
        if max_questions and stats["total_generated"] >= max_questions:
            print(f"  → 전체 상한 {max_questions}개 도달, 나머지 {len(targets) - i + 1}개 조합 스킵")
            break

        label = f"[{target['question_type']}] {target['node_name'][:35]}"
        print(f"  ({i}/{len(targets)}) {label} ...", end=" ", flush=True)

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
            stats["failed"] += 1
            continue

        job_id = resp.json()["job_id"]

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
            questions = result if isinstance(result, list) else result.get("questions", [])
            for q in questions:
                all_questions.append({
                    **q,
                    "entity_id": target["node_id"],
                    "question_type": target["question_type"],
                })
            stats["total_generated"] += len(questions)
            print(f"완료 ({len(questions)}개, 누적 {stats['total_generated']}개)")
            stats["success"] += 1
        elif status == "failed":
            print(f"실패: {job.get('error', '')[:60]}")
            stats["failed"] += 1
        else:
            print(f"타임아웃 (job_id={job_id})")
            stats["skipped"] += 1

    # 파일 덤프
    ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S")
    out_file = output_dir / f"questions_{subject['id'][:8]}_{ts}.json"
    out_file.write_text(json.dumps({
        "subject_id": subject["id"],
        "subject_name": subject["name"],
        "generated_at": ts,
        "stats": stats,
        "questions": all_questions,
    }, ensure_ascii=False, indent=2))

    print(f"\n  → 덤프 완료: {out_file}  ({len(all_questions)}개)")
    return out_file


# ── Step 5: 파일 로드 → storage API 저장 ─────────────────────────────────────

def load_and_save(client: httpx.Client, dump_file: Path) -> dict:
    """덤프 파일을 읽어 storage API로 question_items에 저장."""
    data = json.loads(dump_file.read_text())
    questions = data.get("questions", [])

    print(f"[5/5] DB 저장 시작 ({len(questions)}개, 파일: {dump_file.name})")

    saved, failed = 0, 0
    for q in questions:
        payload = {
            "entity_id": q["entity_id"],
            "question_text": q["question_text"],
            "options": q.get("options", []),
            "correct_answer": q["correct_answer"],
            "explanation": q.get("explanation"),
            "node_snapshot": q.get("node_snapshot"),
            "question_type": q.get("question_type", "MCQ"),
            "difficulty": q.get("difficulty_level", "medium"),
        }
        resp = client.post("/api/question-workbench/questions", json=payload)
        if resp.status_code in (200, 201):
            saved += 1
        else:
            failed += 1

    print(f"  → 저장 완료: {saved}개 성공 / {failed}개 실패")
    return {"saved": saved, "failed": failed}


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="문제 생성 파이프라인")
    parser.add_argument("--subject-id", help="대상 subject ID")
    parser.add_argument("--config", default=str(Path(__file__).parent / "config.yaml"))
    parser.add_argument("--dry-run", action="store_true", help="대상 선정까지만 실행 (생성 안 함)")
    parser.add_argument("--load-and-save", metavar="FILE", help="덤프 파일을 로드하여 DB에 저장")
    args = parser.parse_args()

    cfg = load_config(args.config)
    base_url = cfg["api"]["base_url"]

    with httpx.Client(base_url=base_url, timeout=30) as client:
        token = authenticate(client, cfg)
        client.headers["Authorization"] = f"Bearer {token}"

        # load-and-save 단독 실행
        if args.load_and_save:
            result = load_and_save(client, Path(args.load_and_save))
            print(f"\n완료: {result['saved']}개 저장 / {result['failed']}개 실패")
            return

        if not args.subject_id:
            parser.error("--subject-id 또는 --load-and-save 중 하나가 필요합니다")

        subject = get_subject(client, args.subject_id)
        targets = analyze_and_select_targets(client, subject, cfg)

        if not targets:
            print("강화 대상 없음 — 종료")
            return

        if args.dry_run:
            print("[dry-run] 생성 단계 스킵")
            return

        # Step 4: 생성 + 파일 덤프
        out_file = generate_and_dump(client, subject, targets, cfg)

        # Step 5: 파일 → DB 저장
        print()
        result = load_and_save(client, out_file)

    print()
    print("=" * 50)
    print(f"완료: DB 저장 {result['saved']}개 / 실패 {result['failed']}개")


if __name__ == "__main__":
    main()
