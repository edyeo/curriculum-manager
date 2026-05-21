"""
가상 학생 답변 합성 데이터 파이프라인

Usage:
  python pipeline.py --subject-id <id>            # 전체 실행
  python pipeline.py --subject-id <id> --dry-run  # 대상 선정까지만
  python pipeline.py --load-and-save <file>       # 덤프 파일 → DB 적재
"""
import argparse
import json
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

import httpx
import yaml

import db as dbmod


def load_config(path: str) -> dict:
    with open(path) as f:
        return yaml.safe_load(f)


def build_persona(student: dict) -> dict:
    """virtual-student-api feature_values → persona dict 구성."""
    return student.get("features", {})


# ── Step 1~2: Extract ─────────────────────────────────────────────────────────

def extract_data(cfg: dict, subject_id: str) -> tuple[list, list]:
    sp_engine = dbmod.get_engine(cfg["databases"]["student_platform"])
    cm_engine = dbmod.get_engine(cfg["databases"]["contents_manager"])
    vs_engine = dbmod.get_engine(cfg["databases"]["virtual_student"])
    sim = cfg["simulation"]

    print("[1/5] 가상 학생 프로파일 추출 중...")
    students = dbmod.fetch_virtual_students(sp_engine, subject_id, sim["max_students"])
    print(f"  → {len(students)}명 (virtual_students 테이블)")

    print("[1.5/5] Feature values 로드 중...")
    for s in students:
        s["features"] = dbmod.fetch_virtual_student_features(vs_engine, s["vs_api_id"])
    print(f"  → 완료")

    print("[2/5] 발행된 문제 추출 중...")
    questions = dbmod.fetch_questions(cm_engine, subject_id, sim["question_types"], sim["max_questions_per_student"])
    print(f"  → {len(questions)}개")

    return students, questions


# ── Step 3: Target 선정 ────────────────────────────────────────────────────────

def select_targets(cfg: dict, students: list, questions: list) -> list[dict]:
    """미답변 (student × question) 조합 선정."""
    sp_engine = dbmod.get_engine(cfg["databases"]["student_platform"])

    print("[3/5] 미답변 타겟 선정 중...")
    targets = []
    total_already = 0
    for student in students:
        answered = dbmod.fetch_answered_question_ids(sp_engine, student["id"])
        unanswered = [q for q in questions if q["id"] not in answered]
        total_already += len(answered)
        if unanswered:
            targets.append({"student": student, "questions": unanswered})

    total_new = sum(len(t["questions"]) for t in targets)
    print(f"  → {len(targets)}명 대상 / 총 {total_new}개 답변 예정 (기존 {total_already}개 제외)")
    return targets


# ── Step 4: 가상 답변 생성 + 파일 덤프 ────────────────────────────────────────

def generate_and_dump(targets: list, subject_id: str, cfg: dict) -> Path:
    vs_url = cfg["api"]["virtual_student_url"]
    timeout = cfg["simulation"].get("request_timeout", 60)
    output_dir = Path(__file__).parent / cfg.get("output_dir", "../../data/output")
    output_dir.mkdir(parents=True, exist_ok=True)

    stats = {"students": len(targets), "total_targets": 0, "success": 0, "failed": 0}
    all_answers: list[dict] = []

    total_q = sum(len(t["questions"]) for t in targets)
    print(f"[4/5] 가상 답변 생성 시작 ({len(targets)}명 × 최대 {total_q}문제)")

    with httpx.Client(base_url=vs_url, timeout=timeout) as client:
        for i, target in enumerate(targets, 1):
            student = target["student"]
            questions = target["questions"]
            persona = build_persona(student)

            print(f"  ({i}/{len(targets)}) {student['name']} [{len(questions)}문제] ...", end=" ", flush=True)

            payload = {
                "name": student["name"],
                "persona": persona,
                "subject_id": subject_id,
                "questions": [
                    {
                        "question_id": q["id"],
                        "question_text": q["question_text"],
                        "question_type": q["question_type"],
                        "options": q.get("options") or [],
                        "correct_answer": q.get("correct_answer") or "",
                    }
                    for q in questions
                ],
            }

            try:
                resp = client.post("/api/simulate/generate-and-grade", json=payload)
                resp.raise_for_status()
                answers = resp.json()

                for a, q in zip(answers, questions):
                    all_answers.append({
                        "student_id": student["id"],
                        "question_id": q["id"],
                        "node_id": q["entity_id"],
                        "subject_id": subject_id,
                        "question_text": q["question_text"],
                        "question_type": q["question_type"],
                        "correct_answer": q.get("correct_answer", ""),
                        "user_answer": a.get("answer_text", ""),
                        "is_correct": a.get("is_correct"),
                        "score": a.get("score"),
                        "feedback": a.get("feedback", ""),
                        "time_taken_seconds": 0,
                    })
                stats["success"] += 1
                stats["total_targets"] += len(answers)
                print(f"완료 ({len(answers)}개)")
            except Exception as e:
                print(f"실패: {str(e)[:80]}")
                stats["failed"] += 1

    ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S")
    out_file = output_dir / f"student_answers_{subject_id[:8]}_{ts}.json"
    out_file.write_text(json.dumps({
        "subject_id": subject_id,
        "generated_at": ts,
        "stats": stats,
        "answers": all_answers,
    }, ensure_ascii=False, indent=2))

    print(f"\n  → 덤프 완료: {out_file}  (총 {len(all_answers)}개)")
    return out_file


# ── Step 5: 덤프 파일 → DB 직접 적재 ─────────────────────────────────────────

def load_to_db(cfg: dict, dump_file: Path) -> dict:
    data = json.loads(dump_file.read_text())
    answers = data.get("answers", [])

    print(f"[5/5] DB 적재 시작 ({len(answers)}개, 파일: {dump_file.name})")

    sp_engine = dbmod.get_engine(cfg["databases"]["student_platform"])
    now = datetime.now(timezone.utc).replace(tzinfo=None)

    session_rows = [
        {
            "student_id": a["student_id"],
            "question_id": a["question_id"],
            "node_id": a["node_id"],
            "subject_id": a["subject_id"],
            "user_answer": a.get("user_answer", ""),
            "is_correct": a.get("is_correct"),
            "score": a.get("score"),
            "feedback": a.get("feedback", ""),
            "time_taken_seconds": a.get("time_taken_seconds", 0),
            "created_at": now,
        }
        for a in answers
    ]
    inserted = dbmod.insert_study_sessions(sp_engine, session_rows)
    print(f"  virtual_study_sessions: {inserted}개 INSERT")

    grouped: dict[tuple, list] = defaultdict(list)
    for a in answers:
        grouped[(a["student_id"], a["node_id"], a["subject_id"])].append(a)

    mastery_updates = 0
    for (student_id, node_id, subject_id), group in grouped.items():
        for a in group:
            dbmod.upsert_node_mastery(
                sp_engine,
                student_id=student_id,
                node_id=node_id,
                subject_id=subject_id,
                is_correct=bool(a.get("is_correct")),
                score=float(a.get("score") or 0.0),
            )
            mastery_updates += 1

    print(f"  virtual_node_mastery: {mastery_updates}개 UPSERT")
    return {"inserted": inserted, "mastery_updates": mastery_updates}


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="가상 학생 답변 합성 데이터 파이프라인")
    parser.add_argument("--subject-id", help="대상 subject ID")
    parser.add_argument("--config", default=str(Path(__file__).parent / "config.yaml"))
    parser.add_argument("--dry-run", action="store_true", help="대상 선정까지만 실행 (생성 안 함)")
    parser.add_argument("--load-and-save", metavar="FILE", help="덤프 파일 → DB 적재")
    args = parser.parse_args()

    cfg = load_config(args.config)

    if args.load_and_save:
        result = load_to_db(cfg, Path(args.load_and_save))
        print(f"\n완료: {result['inserted']}개 세션 / {result['mastery_updates']}개 숙련도 갱신")
        return

    if not args.subject_id:
        parser.error("--subject-id 또는 --load-and-save 중 하나가 필요합니다")

    students, questions = extract_data(cfg, args.subject_id)

    if not students:
        print("가상 학생 없음 — 종료 (virtual-student-api에서 먼저 생성하세요)")
        return
    if not questions:
        print("발행된 문제 없음 — 종료")
        return

    targets = select_targets(cfg, students, questions)

    if not targets:
        print("미답변 타겟 없음 — 종료")
        return

    if args.dry_run:
        print("[dry-run] 생성 단계 스킵")
        return

    out_file = generate_and_dump(targets, args.subject_id, cfg)
    print()
    result = load_to_db(cfg, out_file)

    print()
    print("=" * 50)
    print(f"완료: {result['inserted']}개 세션 / {result['mastery_updates']}개 숙련도 갱신")


if __name__ == "__main__":
    main()
