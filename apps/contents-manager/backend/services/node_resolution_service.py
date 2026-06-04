"""학생 데이터 기반 Concept 노드 이상 검출 서비스 — T_STUDENT용.

이상 탐지 기준:
  Concept 노드 A의 후행 노드(B, C, D) 간 weighted_score 상관이 낮으면
  A가 하위 개념을 혼재한 이상 노드로 판정.

  weighted_score = is_correct × level_weight(mastery_before)
  level_weight: LOW(0~0.4)=0.5, MID(0.4~0.7)=1.0, HIGH(0.7~1.0)=1.5
"""
import logging
import os
import statistics
from collections import defaultdict

from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine

logger = logging.getLogger(__name__)


_LEVEL_WEIGHTS = [
    (0.4, 0.5),   # mastery_before < 0.4 → weight 0.5
    (0.7, 1.0),   # mastery_before < 0.7 → weight 1.0
    (1.1, 1.5),   # mastery_before >= 0.7 → weight 1.5
]


def _level_weight(mastery_before: float | None) -> float:
    if mastery_before is None:
        return 1.0
    for threshold, weight in _LEVEL_WEIGHTS:
        if mastery_before < threshold:
            return weight
    return 1.5


def _get_student_engine() -> Engine:
    url = os.getenv(
        "STUDENT_PLATFORM_DB_URL",
        "sqlite:////app/db/student_platform.db",
    )
    connect_args = {"check_same_thread": False} if url.startswith("sqlite") else {}
    return create_engine(url, connect_args=connect_args)


def _get_cm_engine() -> Engine:
    from database import engine
    return engine


def fetch_concept_successor_pairs(cm_engine: Engine, subject_id: str) -> dict[str, list[str]]:
    """Concept 노드별 후행 노드(requires/has_subtopic) 목록 반환.

    Returns: {concept_node_id: [successor_node_id, ...]}
    """
    with cm_engine.connect() as conn:
        rows = conn.execute(
            text("""
                SELECT e.source_id, e.target_id
                FROM kg_edges e
                JOIN kg_nodes src ON src.id = e.source_id
                WHERE src.subject_id = :subj
                  AND src.type = 'Concept'
                  AND e.relation_type IN ('requires', 'has_subtopic')
            """),
            {"subj": subject_id},
        ).fetchall()

    successors: dict[str, list[str]] = defaultdict(list)
    for source_id, target_id in rows:
        successors[source_id].append(target_id)
    return dict(successors)


def fetch_weighted_scores(
    sp_engine: Engine,
    subject_id: str,
    node_ids: list[str],
) -> dict[tuple[int, str], float]:
    """(student_id, node_id) → weighted_score 매핑 반환.

    virtual_student_study_log + virtual_student_study_session_info 조인으로
    mastery_before 기반 가중치 적용 평균 산출.
    """
    if not node_ids:
        return {}

    placeholders = ", ".join(f":nid{i}" for i in range(len(node_ids)))
    params: dict = {"subj": subject_id}
    for i, nid in enumerate(node_ids):
        params[f"nid{i}"] = nid

    with sp_engine.connect() as conn:
        rows = conn.execute(
            text(f"""
                SELECT vas.student_id,
                       vas.node_id,
                       vss.is_correct,
                       vas.mastery_before
                FROM virtual_student_study_log vss
                JOIN virtual_student_study_session_info vas ON vas.session_id = vss.session_id
                WHERE vas.subject_id = :subj
                  AND vas.node_id IN ({placeholders})
                  AND vss.is_correct IS NOT NULL
            """),
            params,
        ).fetchall()

    # (student_id, node_id) → [weighted_score, ...]
    score_map: dict[tuple[int, str], list[float]] = defaultdict(list)
    for student_id, node_id, is_correct, mastery_before in rows:
        w = _level_weight(mastery_before)
        score_map[(student_id, node_id)].append(int(is_correct) * w)

    return {k: statistics.mean(v) for k, v in score_map.items()}


def fetch_node_correctness(
    sp_engine: Engine,
    subject_id: str,
    node_ids: list[str],
) -> dict[str, dict]:
    """노드별 정답 통계 반환 — degenerate(무변별) 노드 판정용.

    Returns: {node_id: {"total": 답변수, "correct": 정답수, "students": 응시 학생수}}
    """
    if not node_ids:
        return {}

    placeholders = ", ".join(f":nid{i}" for i in range(len(node_ids)))
    params: dict = {"subj": subject_id}
    for i, nid in enumerate(node_ids):
        params[f"nid{i}"] = nid

    with sp_engine.connect() as conn:
        rows = conn.execute(
            text(f"""
                SELECT vas.node_id,
                       COUNT(*) AS total,
                       SUM(CASE WHEN vss.is_correct THEN 1 ELSE 0 END) AS correct,
                       COUNT(DISTINCT vas.student_id) AS students
                FROM virtual_student_study_log vss
                JOIN virtual_student_study_session_info vas ON vas.session_id = vss.session_id
                WHERE vas.subject_id = :subj
                  AND vas.node_id IN ({placeholders})
                  AND vss.is_correct IS NOT NULL
                GROUP BY vas.node_id
            """),
            params,
        ).fetchall()

    return {
        r[0]: {"total": int(r[1]), "correct": int(r[2] or 0), "students": int(r[3])}
        for r in rows
    }


def detect_degenerate_nodes(
    correctness: dict[str, dict],
    node_meta: dict[str, dict],
    min_students: int,
) -> list[dict]:
    """전부 정답(또는 전부 오답)인 무변별 노드 검출 — 개념 이상 신호.

    한 노드에서 충분한 학생이 응시했는데 정답률이 1.0/0.0으로 변별이 전혀
    없으면, 문제·개념 자체에 이상이 있을 가능성이 높다(너무 쉽거나/잘못된 정답키 등).
    """
    degenerate = []
    for node_id, s in correctness.items():
        if s["students"] < min_students or s["total"] == 0:
            continue
        rate = s["correct"] / s["total"]
        if rate not in (0.0, 1.0):
            continue
        meta = node_meta.get(node_id, {})
        kind = "전 학생 정답" if rate == 1.0 else "전 학생 오답"
        degenerate.append({
            "node_id": node_id,
            "name": meta.get("name", ""),
            "type": meta.get("type", ""),
            "depth": meta.get("depth"),
            "sample_students": s["students"],
            "answer_count": s["total"],
            "correct_rate": round(rate, 4),
            "reason_code": "all_correct" if rate == 1.0 else "all_incorrect",
            "reason": f"{kind} (응답 {s['students']}명) — 변별력 없음, 개념·문제 점검 필요",
        })
    degenerate.sort(key=lambda x: (-x["sample_students"], x["node_id"]))
    return degenerate


def _pearson_correlation(xs: list[float], ys: list[float]) -> float | None:
    """피어슨 상관계수. 샘플 부족 시 None 반환."""
    n = len(xs)
    if n < 3:
        return None
    mean_x = statistics.mean(xs)
    mean_y = statistics.mean(ys)
    num = sum((x - mean_x) * (y - mean_y) for x, y in zip(xs, ys))
    den_x = sum((x - mean_x) ** 2 for x in xs) ** 0.5
    den_y = sum((y - mean_y) ** 2 for y in ys) ** 0.5
    if den_x == 0 or den_y == 0:
        return None
    return num / (den_x * den_y)


def compute_anomaly_scores(
    subject_id: str,
    top_k: int = 50,
    min_students: int = 10,
    min_successors: int = 3,
    cm_engine: Engine | None = None,
    sp_engine: Engine | None = None,
) -> dict:
    """Concept 노드 이상 스코어 계산 후 TOP-K + 진단 정보 반환.

    Returns:
        {
            "anomalies": [...],          # 이상 스코어 TOP-K
            "diagnostics": {
                "params": {...},
                "process": [단계 설명, ...],
                "concept_total": int,    # 후행 보유 Concept 수
                "candidate_count": int,  # 후행>=min_successors 후보 수
                "evaluated": [           # 후보별 진단 (포함/제외 사유)
                    {"node_id", "name", "successor_count",
                     "successors_with_data", "common_students",
                     "correlation_pairs", "anomaly_score",
                     "status": "included"|"excluded", "reason"},
                    ...
                ],
            },
        }

    엔진은 테스트 주입을 위해 인자로 받을 수 있다 (None이면 기본 연결).
    상관 계산은 **데이터가 있는 후행 노드만** 대상으로 한다 — 데이터 없는
    후행을 교집합에 포함하면 공통 학생이 항상 0이 되어 검출이 불가능하다.
    """
    cm_engine = cm_engine or _get_cm_engine()
    sp_engine = sp_engine or _get_student_engine()

    diagnostics: dict = {
        "params": {
            "top_k": top_k,
            "min_students": min_students,
            "min_successors": min_successors,
        },
        "process": [],
        "concept_total": 0,
        "candidate_count": 0,
        "evaluated": [],
    }
    proc: list[str] = diagnostics["process"]

    # Subject 전체 노드 수 (검사 모수)
    with cm_engine.connect() as conn:
        subject_node_total = conn.execute(
            text("SELECT COUNT(*) FROM kg_nodes WHERE subject_id = :subj"),
            {"subj": subject_id},
        ).scalar() or 0
    diagnostics["subject_node_total"] = subject_node_total
    diagnostics["analyzed_concept_count"] = 0
    diagnostics["analyzed_successor_count"] = 0
    proc.append(f"Subject 전체 노드: {subject_node_total}개")

    # Concept → 후행 노드 목록
    successors_map = fetch_concept_successor_pairs(cm_engine, subject_id)
    diagnostics["concept_total"] = len(successors_map)
    proc.append(f"후행 보유 Concept 수집: {len(successors_map)}개")

    # 후행 노드가 min_successors 이상인 Concept만 대상
    candidates = {
        nid: succs
        for nid, succs in successors_map.items()
        if len(succs) >= min_successors
    }
    diagnostics["candidate_count"] = len(candidates)
    proc.append(f"후행>={min_successors} 후보 선정: {len(candidates)}개")
    if not candidates:
        proc.append("후보 없음 — 종료")
        return {"anomalies": [], "degenerate_nodes": [], "diagnostics": diagnostics}

    # 후행 노드 전체 목록 수집 후 weighted_score 일괄 조회
    all_successor_ids = list({s for succs in candidates.values() for s in succs})
    score_map = fetch_weighted_scores(sp_engine, subject_id, all_successor_ids)
    proc.append(
        f"후행 weighted_score 조회: {len(score_map)}개 (student,node) 쌍 / "
        f"데이터 보유 후행 {len({nid for (_, nid) in score_map})}개"
    )

    # Concept·후행 노드 메타 일괄 조회 (degenerate 노드 이름 표기 포함)
    meta_ids = list({*candidates.keys(), *all_successor_ids})
    placeholders = ", ".join(f":cid{i}" for i in range(len(meta_ids)))
    params = {f"cid{i}": v for i, v in enumerate(meta_ids)}
    params["subj"] = subject_id
    with cm_engine.connect() as conn:
        node_rows = conn.execute(
            text(f"""
                SELECT id, name, type, depth
                FROM kg_nodes
                WHERE subject_id = :subj AND id IN ({placeholders})
            """),
            params,
        ).fetchall()
    node_meta = {r[0]: {"name": r[1], "type": r[2], "depth": r[3]} for r in node_rows}

    results = []
    for concept_id, successor_ids in candidates.items():
        meta = node_meta.get(concept_id, {})
        entry: dict = {
            "node_id": concept_id,
            "name": meta.get("name", ""),
            "successor_count": len(successor_ids),
            "successors_with_data": 0,
            "common_students": 0,
            "correlation_pairs": 0,
            "anomaly_score": None,
        }

        # 후행별 데이터 보유 학생 집합 — 데이터 있는 후행만 대상으로 한다
        per_successor_students = {
            succ_id: {sid for (sid, nid) in score_map if nid == succ_id}
            for succ_id in successor_ids
        }
        successors_with_data = [s for s, studs in per_successor_students.items() if studs]
        entry["successors_with_data"] = len(successors_with_data)

        if len(successors_with_data) < 2:
            entry["status"] = "excluded"
            entry["reason_code"] = "insufficient_successor_data"
            entry["reason"] = (
                f"데이터 보유 후행 {len(successors_with_data)}개 (<2) — 상관 계산 불가"
            )
            diagnostics["evaluated"].append(entry)
            continue

        # 데이터 있는 후행 전체에 점수를 가진 공통 학생 교집합
        common_students = set.intersection(
            *[per_successor_students[s] for s in successors_with_data]
        )
        entry["common_students"] = len(common_students)

        if len(common_students) < min_students:
            entry["status"] = "excluded"
            entry["reason_code"] = "insufficient_common_students"
            entry["reason"] = f"공통 학생 {len(common_students)}명 (<{min_students})"
            diagnostics["evaluated"].append(entry)
            continue

        students = sorted(common_students)
        successor_scores = [
            [score_map.get((sid, succ_id), 0.0) for sid in students]
            for succ_id in successors_with_data
        ]

        # 후행 노드 쌍별 상관계수 평균
        correlations = []
        for i in range(len(successors_with_data)):
            for j in range(i + 1, len(successors_with_data)):
                corr = _pearson_correlation(successor_scores[i], successor_scores[j])
                if corr is not None:
                    correlations.append(corr)
        entry["correlation_pairs"] = len(correlations)

        if not correlations:
            entry["status"] = "excluded"
            entry["reason_code"] = "no_variance"
            entry["reason"] = (
                f"유효 상관 쌍 없음 (공통 학생 {len(common_students)}명, 점수 분산 부족)"
            )
            diagnostics["evaluated"].append(entry)
            continue

        avg_corr = statistics.mean(correlations)
        anomaly_score = round(1.0 - avg_corr, 4)
        entry["anomaly_score"] = anomaly_score
        entry["status"] = "included"
        entry["reason_code"] = "computed"
        entry["reason"] = "이상 스코어 산출 완료"
        diagnostics["evaluated"].append(entry)

        results.append({
            "node_id": concept_id,
            "name": meta.get("name", ""),
            "type": meta.get("type", "Concept"),
            "depth": meta.get("depth"),
            "successor_count": len(successor_ids),
            "successors_with_data": len(successors_with_data),
            "avg_successor_correlation": round(avg_corr, 4),
            "anomaly_score": anomaly_score,
            "sample_students": len(common_students),
        })

    results.sort(key=lambda x: x["anomaly_score"], reverse=True)
    included = len(results)

    # 제외 사유별 노드 추출 — 분석 불가(no_variance) / 데이터·학생 부족 분류
    excluded_summary: dict[str, list[str]] = {
        "insufficient_successor_data": [],
        "insufficient_common_students": [],
        "no_variance": [],
    }
    for e in diagnostics["evaluated"]:
        code = e.get("reason_code")
        if code in excluded_summary:
            excluded_summary[code].append(e["node_id"])
    diagnostics["excluded_summary"] = excluded_summary

    # 무변별(전부 정답/오답) 노드 검출 — 상관 분석과 별개의 개념 이상 신호
    correctness = fetch_node_correctness(sp_engine, subject_id, all_successor_ids)
    degenerate_nodes = detect_degenerate_nodes(correctness, node_meta, min_students)
    diagnostics["degenerate_count"] = len(degenerate_nodes)

    # 실제 분석에 투입된 노드 수 — 상관 분석 후보 Concept + 데이터 보유 후행
    diagnostics["analyzed_concept_count"] = len(candidates)
    diagnostics["analyzed_successor_count"] = len(correctness)

    uncomputable = excluded_summary["no_variance"]
    proc.append(
        f"검출 완료: 포함 {included}개 / 제외 {len(candidates) - included}개 "
        f"(분석 불가 {len(uncomputable)}개, 데이터 부족 "
        f"{len(excluded_summary['insufficient_successor_data'])}개, 학생 부족 "
        f"{len(excluded_summary['insufficient_common_students'])}개) / "
        f"무변별(개념 이상) {len(degenerate_nodes)}개"
    )

    # 평가 불가 노드 개수 + 사유별 id 로그 기록
    logger.info(
        "[node-resolution] subject=%s 후보=%d 검출=%d 분석불가=%d 데이터부족=%d 학생부족=%d 무변별=%d",
        subject_id, len(candidates), included, len(uncomputable),
        len(excluded_summary["insufficient_successor_data"]),
        len(excluded_summary["insufficient_common_students"]),
        len(degenerate_nodes),
    )
    if uncomputable:
        logger.info("[node-resolution] 분석불가(no_variance) ids=%s", uncomputable)
    if excluded_summary["insufficient_successor_data"]:
        logger.info(
            "[node-resolution] 데이터부족(insufficient_successor_data) ids=%s",
            excluded_summary["insufficient_successor_data"],
        )
    if excluded_summary["insufficient_common_students"]:
        logger.info(
            "[node-resolution] 학생부족(insufficient_common_students) ids=%s",
            excluded_summary["insufficient_common_students"],
        )
    if degenerate_nodes:
        logger.warning(
            "[node-resolution] 무변별(개념 이상) ids=%s",
            [d["node_id"] for d in degenerate_nodes],
        )

    return {
        "anomalies": results[:top_k],
        "degenerate_nodes": degenerate_nodes,
        "diagnostics": diagnostics,
    }
