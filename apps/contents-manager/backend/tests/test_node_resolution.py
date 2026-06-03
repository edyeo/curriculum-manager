"""node_resolution_service 통합 테스트 — test data로 이상 노드 검출 로직 검증.

실 DB 대신 임시 SQLite(cm/sp) 2개를 구성해 compute_anomaly_scores에 주입한다.
weighted_score = is_correct × level_weight(mastery_before) 이므로
mastery_before를 고정(0.5 → weight 1.0)하면 score = is_correct 가 되어
후행 노드 간 상관을 의도대로 제어할 수 있다.
"""
import pytest
from sqlalchemy import create_engine, text

from services.node_resolution_service import compute_anomaly_scores

SUBJ = "subj-1"


# ── 테스트 DB 헬퍼 ────────────────────────────────────────────────────────────

def _make_cm_engine(tmp_path, nodes, edges):
    """nodes: [(id, type, depth)], edges: [(source, target, relation)]."""
    eng = create_engine(f"sqlite:///{tmp_path}/cm.db")
    with eng.begin() as c:
        c.execute(text(
            "CREATE TABLE kg_nodes (id TEXT PRIMARY KEY, subject_id TEXT, "
            "name TEXT, type TEXT, depth INTEGER)"
        ))
        c.execute(text(
            "CREATE TABLE kg_edges (source_id TEXT, target_id TEXT, relation_type TEXT)"
        ))
        for nid, ntype, depth in nodes:
            c.execute(
                text("INSERT INTO kg_nodes VALUES (:id, :s, :n, :t, :d)"),
                {"id": nid, "s": SUBJ, "n": f"name-{nid}", "t": ntype, "d": depth},
            )
        for src, tgt, rel in edges:
            c.execute(
                text("INSERT INTO kg_edges VALUES (:s, :t, :r)"),
                {"s": src, "t": tgt, "r": rel},
            )
    return eng


def _make_sp_engine(tmp_path, records):
    """records: [(student_id, node_id, is_correct, mastery_before)].

    (student, node)당 세션 1개 + 로그 1개 생성 → weighted_score = is_correct × weight.
    """
    eng = create_engine(f"sqlite:///{tmp_path}/sp.db")
    with eng.begin() as c:
        c.execute(text(
            "CREATE TABLE virtual_student_study_session_info ("
            "session_id TEXT PRIMARY KEY, student_id INTEGER, node_id TEXT, "
            "subject_id TEXT, mastery_before REAL, mastery_after REAL)"
        ))
        c.execute(text(
            "CREATE TABLE virtual_student_study_log ("
            "id INTEGER PRIMARY KEY AUTOINCREMENT, session_id TEXT, student_id INTEGER, "
            "node_id TEXT, subject_id TEXT, is_correct INTEGER)"
        ))
        for i, (sid, nid, ic, mb) in enumerate(records):
            session_id = f"sess-{i}"
            c.execute(
                text(
                    "INSERT INTO virtual_student_study_session_info "
                    "(session_id, student_id, node_id, subject_id, mastery_before) "
                    "VALUES (:sess, :sid, :nid, :subj, :mb)"
                ),
                {"sess": session_id, "sid": sid, "nid": nid, "subj": SUBJ, "mb": mb},
            )
            c.execute(
                text(
                    "INSERT INTO virtual_student_study_log "
                    "(session_id, student_id, node_id, subject_id, is_correct) "
                    "VALUES (:sess, :sid, :nid, :subj, :ic)"
                ),
                {"sess": session_id, "sid": sid, "nid": nid, "subj": SUBJ, "ic": ic},
            )
    return eng


def _records_for_node(node_id, correctness, mastery_before=0.5):
    """학생 1..N에 대해 (sid, node, is_correct, mb) 레코드 생성."""
    return [
        (sid, node_id, ic, mastery_before)
        for sid, ic in enumerate(correctness, start=1)
    ]


# ── 테스트 ────────────────────────────────────────────────────────────────────

def test_anomaly_detected_for_diverging_successors(tmp_path):
    """후행 X, Y가 반대 패턴(음의 상관) → 이상 노드로 검출."""
    cm = _make_cm_engine(
        tmp_path,
        nodes=[("C1", "Concept", 1), ("X", "Concept", 2), ("Y", "Concept", 2)],
        edges=[("C1", "X", "requires"), ("C1", "Y", "requires")],
    )
    sp = _make_sp_engine(
        tmp_path,
        _records_for_node("X", [1, 1, 1, 0, 0])
        + _records_for_node("Y", [0, 0, 0, 1, 1]),
    )

    out = compute_anomaly_scores(
        SUBJ, min_students=3, min_successors=2, cm_engine=cm, sp_engine=sp
    )

    assert len(out["anomalies"]) == 1
    a = out["anomalies"][0]
    assert a["node_id"] == "C1"
    # X·Y 완전 음의 상관(-1) → anomaly_score = 1 - (-1) = 2.0
    assert a["anomaly_score"] == pytest.approx(2.0)
    assert a["sample_students"] == 5
    # 진단: included
    ev = {e["node_id"]: e for e in out["diagnostics"]["evaluated"]}
    assert ev["C1"]["status"] == "included"


def test_low_anomaly_for_correlated_successors(tmp_path):
    """후행 X, Y가 동일 패턴(양의 상관) → 낮은 이상 스코어로 포함."""
    cm = _make_cm_engine(
        tmp_path,
        nodes=[("C1", "Concept", 1), ("X", "Concept", 2), ("Y", "Concept", 2)],
        edges=[("C1", "X", "requires"), ("C1", "Y", "has_subtopic")],
    )
    sp = _make_sp_engine(
        tmp_path,
        _records_for_node("X", [1, 1, 1, 0, 0])
        + _records_for_node("Y", [1, 1, 1, 0, 0]),
    )

    out = compute_anomaly_scores(
        SUBJ, min_students=3, min_successors=2, cm_engine=cm, sp_engine=sp
    )

    assert len(out["anomalies"]) == 1
    # 완전 양의 상관(+1) → anomaly_score = 1 - 1 = 0.0
    assert out["anomalies"][0]["anomaly_score"] == pytest.approx(0.0)


def test_excluded_when_common_students_below_min(tmp_path):
    """공통 학생 < min_students → 제외 + 진단 사유."""
    cm = _make_cm_engine(
        tmp_path,
        nodes=[("C1", "Concept", 1), ("X", "Concept", 2), ("Y", "Concept", 2)],
        edges=[("C1", "X", "requires"), ("C1", "Y", "requires")],
    )
    sp = _make_sp_engine(
        tmp_path,
        _records_for_node("X", [1, 1, 1, 0, 0])
        + _records_for_node("Y", [0, 0, 0, 1, 1]),
    )

    out = compute_anomaly_scores(
        SUBJ, min_students=10, min_successors=2, cm_engine=cm, sp_engine=sp
    )

    assert out["anomalies"] == []
    ev = {e["node_id"]: e for e in out["diagnostics"]["evaluated"]}
    assert ev["C1"]["status"] == "excluded"
    assert "공통 학생" in ev["C1"]["reason"]
    assert ev["C1"]["common_students"] == 5


def test_excluded_when_fewer_than_two_successors_have_data(tmp_path):
    """후행 2개 중 1개만 데이터 → 상관 불가로 제외 + 진단 사유."""
    cm = _make_cm_engine(
        tmp_path,
        nodes=[("C1", "Concept", 1), ("X", "Concept", 2), ("Y", "Concept", 2)],
        edges=[("C1", "X", "requires"), ("C1", "Y", "requires")],
    )
    # Y에는 데이터 없음
    sp = _make_sp_engine(tmp_path, _records_for_node("X", [1, 1, 1, 0, 0]))

    out = compute_anomaly_scores(
        SUBJ, min_students=3, min_successors=2, cm_engine=cm, sp_engine=sp
    )

    assert out["anomalies"] == []
    ev = {e["node_id"]: e for e in out["diagnostics"]["evaluated"]}
    assert ev["C1"]["status"] == "excluded"
    assert ev["C1"]["successors_with_data"] == 1
    assert "데이터 보유 후행" in ev["C1"]["reason"]


def test_partial_successor_data_still_computes(tmp_path):
    """후행 4개 중 2개만 데이터 있어도, 데이터 있는 후행만으로 상관 계산되어 검출.

    (기존 버그: 데이터 없는 후행을 교집합에 포함해 공통 학생이 항상 0이 되던 문제 회귀 방지)
    """
    cm = _make_cm_engine(
        tmp_path,
        nodes=[
            ("C1", "Concept", 1),
            ("X", "Concept", 2), ("Y", "Concept", 2),
            ("Z", "Concept", 2), ("W", "Concept", 2),
        ],
        edges=[
            ("C1", "X", "requires"), ("C1", "Y", "requires"),
            ("C1", "Z", "requires"), ("C1", "W", "requires"),
        ],
    )
    # X, Y에만 데이터 (Z, W는 미수행)
    sp = _make_sp_engine(
        tmp_path,
        _records_for_node("X", [1, 1, 1, 0, 0])
        + _records_for_node("Y", [0, 0, 0, 1, 1]),
    )

    out = compute_anomaly_scores(
        SUBJ, min_students=3, min_successors=3, cm_engine=cm, sp_engine=sp
    )

    assert len(out["anomalies"]) == 1
    a = out["anomalies"][0]
    assert a["node_id"] == "C1"
    assert a["successor_count"] == 4
    assert a["successors_with_data"] == 2
    assert a["anomaly_score"] == pytest.approx(2.0)


def test_no_candidates_when_successors_below_min(tmp_path):
    """후행 수 < min_successors → 후보 없음, 빈 결과 + 진단."""
    cm = _make_cm_engine(
        tmp_path,
        nodes=[("C1", "Concept", 1), ("X", "Concept", 2)],
        edges=[("C1", "X", "requires")],
    )
    sp = _make_sp_engine(tmp_path, _records_for_node("X", [1, 0, 1]))

    out = compute_anomaly_scores(
        SUBJ, min_students=2, min_successors=2, cm_engine=cm, sp_engine=sp
    )

    assert out["anomalies"] == []
    assert out["degenerate_nodes"] == []
    assert out["diagnostics"]["candidate_count"] == 0
    assert out["diagnostics"]["evaluated"] == []
    # 후보가 없어도 전체 검사 모수는 보고됨
    assert out["diagnostics"]["subject_node_total"] == 2  # C1, X


def test_diagnostics_structure(tmp_path):
    """진단 페이로드 구조 검증 — process/params/evaluated 포함."""
    cm = _make_cm_engine(
        tmp_path,
        nodes=[("C1", "Concept", 1), ("X", "Concept", 2), ("Y", "Concept", 2)],
        edges=[("C1", "X", "requires"), ("C1", "Y", "requires")],
    )
    sp = _make_sp_engine(
        tmp_path,
        _records_for_node("X", [1, 1, 0, 0])
        + _records_for_node("Y", [0, 0, 1, 1]),
    )

    out = compute_anomaly_scores(
        SUBJ, min_students=3, min_successors=2, cm_engine=cm, sp_engine=sp
    )

    diag = out["diagnostics"]
    assert diag["params"]["min_students"] == 3
    assert diag["params"]["min_successors"] == 2
    assert isinstance(diag["process"], list) and len(diag["process"]) >= 2
    assert diag["concept_total"] == 1
    assert diag["candidate_count"] == 1
    # 검사 모수/투입 노드 수
    assert diag["subject_node_total"] == 3       # C1, X, Y
    assert diag["analyzed_concept_count"] == 1   # 후보 Concept C1
    assert diag["analyzed_successor_count"] == 2  # 데이터 보유 후행 X, Y
    assert len(diag["evaluated"]) == 1
    entry = diag["evaluated"][0]
    for key in ("node_id", "successor_count", "successors_with_data",
                "common_students", "correlation_pairs", "status", "reason"):
        assert key in entry


# ── 비정상 답변(점수 분산 부족 / 결측) 케이스 ─────────────────────────────────
#
# 실데이터에서 이상 노드가 0개였던 진짜 원인 — 가상 학생 답변이 한 노드에서
# 거의 전부 정답이라 weighted_score 분산이 0이 되어 피어슨 상관을 낼 수 없는
# 상황. 이 경우 후보가 "유효 상관 쌍 없음"으로 제외되어야 하며, 진단에
# common_students 까지 도달했음이 기록되어야 한다.


def test_excluded_when_both_successors_have_no_variance(tmp_path):
    """두 후행 모두 전부 정답(분산 0) → 상관 계산 불가로 제외 + 진단 사유."""
    cm = _make_cm_engine(
        tmp_path,
        nodes=[("C1", "Concept", 1), ("X", "Concept", 2), ("Y", "Concept", 2)],
        edges=[("C1", "X", "requires"), ("C1", "Y", "requires")],
    )
    sp = _make_sp_engine(
        tmp_path,
        _records_for_node("X", [1, 1, 1, 1, 1])
        + _records_for_node("Y", [1, 1, 1, 1, 1]),
    )

    out = compute_anomaly_scores(
        SUBJ, min_students=3, min_successors=2, cm_engine=cm, sp_engine=sp
    )

    assert out["anomalies"] == []
    ev = {e["node_id"]: e for e in out["diagnostics"]["evaluated"]}
    assert ev["C1"]["status"] == "excluded"
    assert ev["C1"]["common_students"] == 5      # 공통 학생까지는 도달
    assert ev["C1"]["correlation_pairs"] == 0    # 유효 상관 쌍 0
    assert "분산 부족" in ev["C1"]["reason"]


def test_excluded_when_one_successor_is_constant(tmp_path):
    """실데이터 ecfd81ea 재현: 한 후행은 분산 있고 다른 후행은 전부 정답.

    분산 0인 후행이 끼면 그 쌍의 상관이 None → 유효 상관 쌍 없음 → 제외.
    """
    cm = _make_cm_engine(
        tmp_path,
        nodes=[("C1", "Concept", 1), ("X", "Concept", 2), ("Y", "Concept", 2)],
        edges=[("C1", "X", "requires"), ("C1", "Y", "requires")],
    )
    sp = _make_sp_engine(
        tmp_path,
        _records_for_node("X", [1, 0, 1, 0, 1])   # 분산 있음
        + _records_for_node("Y", [1, 1, 1, 1, 1]),  # 전부 정답(분산 0)
    )

    out = compute_anomaly_scores(
        SUBJ, min_students=3, min_successors=2, cm_engine=cm, sp_engine=sp
    )

    assert out["anomalies"] == []
    ev = {e["node_id"]: e for e in out["diagnostics"]["evaluated"]}
    assert ev["C1"]["status"] == "excluded"
    assert ev["C1"]["successors_with_data"] == 2
    assert ev["C1"]["common_students"] == 5
    assert ev["C1"]["correlation_pairs"] == 0
    assert "분산 부족" in ev["C1"]["reason"]


def test_excluded_when_all_answers_incorrect(tmp_path):
    """두 후행 모두 전부 오답(분산 0) → 동일하게 상관 불가로 제외."""
    cm = _make_cm_engine(
        tmp_path,
        nodes=[("C1", "Concept", 1), ("X", "Concept", 2), ("Y", "Concept", 2)],
        edges=[("C1", "X", "requires"), ("C1", "Y", "requires")],
    )
    sp = _make_sp_engine(
        tmp_path,
        _records_for_node("X", [0, 0, 0, 0, 0])
        + _records_for_node("Y", [0, 0, 0, 0, 0]),
    )

    out = compute_anomaly_scores(
        SUBJ, min_students=3, min_successors=2, cm_engine=cm, sp_engine=sp
    )

    assert out["anomalies"] == []
    ev = {e["node_id"]: e for e in out["diagnostics"]["evaluated"]}
    assert ev["C1"]["status"] == "excluded"
    assert ev["C1"]["correlation_pairs"] == 0


def test_null_is_correct_is_filtered_out(tmp_path):
    """is_correct가 NULL인 답변은 집계에서 제외 — 후행 데이터 없음으로 처리.

    Y의 모든 답변이 NULL이면 데이터 보유 후행이 X 1개로 줄어 상관 불가.
    """
    cm = _make_cm_engine(
        tmp_path,
        nodes=[("C1", "Concept", 1), ("X", "Concept", 2), ("Y", "Concept", 2)],
        edges=[("C1", "X", "requires"), ("C1", "Y", "requires")],
    )
    sp = _make_sp_engine(
        tmp_path,
        _records_for_node("X", [1, 0, 1, 0, 1])
        + _records_for_node("Y", [None, None, None, None, None]),
    )

    out = compute_anomaly_scores(
        SUBJ, min_students=3, min_successors=2, cm_engine=cm, sp_engine=sp
    )

    assert out["anomalies"] == []
    ev = {e["node_id"]: e for e in out["diagnostics"]["evaluated"]}
    assert ev["C1"]["status"] == "excluded"
    assert ev["C1"]["successors_with_data"] == 1   # Y는 NULL뿐이라 데이터 없음
    assert "데이터 보유 후행" in ev["C1"]["reason"]


def test_constant_successor_does_not_block_variant_pair(tmp_path):
    """후행 3개 중 분산 있는 쌍이 하나라도 있으면 검출 — 분산 0 후행은 무시.

    X·Y는 분산 있어 상관 산출 가능, Z는 전부 정답(분산 0)이라 Z가 낀 쌍만
    None 처리되고 X·Y 쌍으로 이상 스코어가 산출되어야 한다.
    """
    cm = _make_cm_engine(
        tmp_path,
        nodes=[
            ("C1", "Concept", 1),
            ("X", "Concept", 2), ("Y", "Concept", 2), ("Z", "Concept", 2),
        ],
        edges=[
            ("C1", "X", "requires"),
            ("C1", "Y", "requires"),
            ("C1", "Z", "requires"),
        ],
    )
    sp = _make_sp_engine(
        tmp_path,
        _records_for_node("X", [1, 1, 1, 0, 0])
        + _records_for_node("Y", [0, 0, 0, 1, 1])    # X와 음의 상관
        + _records_for_node("Z", [1, 1, 1, 1, 1]),   # 분산 0
    )

    out = compute_anomaly_scores(
        SUBJ, min_students=3, min_successors=3, cm_engine=cm, sp_engine=sp
    )

    assert len(out["anomalies"]) == 1
    a = out["anomalies"][0]
    assert a["node_id"] == "C1"
    assert a["successors_with_data"] == 3
    # 유효 상관은 X·Y 한 쌍뿐 (Z가 낀 쌍은 None)
    ev = {e["node_id"]: e for e in out["diagnostics"]["evaluated"]}
    assert ev["C1"]["correlation_pairs"] == 1
    assert a["anomaly_score"] == pytest.approx(2.0)


# ── 분석 불가 case 추출 + 통합 시나리오 ───────────────────────────────────────
#
# 평가(가상 학생 답변) 후 선후행 관계 분석에서, 한 Subject 안에 검출/제외가
# 공존할 때 이상 노드는 정확히 검출되고 제외 후보는 사유별(reason_code)로
# 추출되어야 한다.
#   - computed                       : 이상 스코어 산출 (anomalies)
#   - no_variance                    : 분석 불가 (점수 분산 부족)
#   - insufficient_successor_data    : 데이터 보유 후행 <2
#   - insufficient_common_students   : 공통 학생 < min_students


def test_reason_codes_assigned_per_exclusion(tmp_path):
    """각 제외 경로가 고유 reason_code로 라벨링되는지 검증."""
    # no_variance
    cm = _make_cm_engine(
        tmp_path,
        nodes=[("C1", "Concept", 1), ("X", "Concept", 2), ("Y", "Concept", 2)],
        edges=[("C1", "X", "requires"), ("C1", "Y", "requires")],
    )
    sp = _make_sp_engine(
        tmp_path,
        _records_for_node("X", [1, 1, 1, 1, 1])
        + _records_for_node("Y", [1, 1, 1, 1, 1]),
    )
    out = compute_anomaly_scores(
        SUBJ, min_students=3, min_successors=2, cm_engine=cm, sp_engine=sp
    )
    ev = {e["node_id"]: e for e in out["diagnostics"]["evaluated"]}
    assert ev["C1"]["reason_code"] == "no_variance"


def test_excluded_summary_extracts_uncomputable_and_insufficient(tmp_path):
    """통합 시나리오 — 검출 + 분석불가 + 데이터부족 + 학생부족 동시 분류.

    평가 후 선후행 분석에서 이상 노드(C_DET)는 검출되고, 나머지 후보들은
    excluded_summary에 사유별로 추출되어야 한다.
    """
    cm = _make_cm_engine(
        tmp_path,
        nodes=[
            # C_DET: 이상 검출 (후행 A·B 음의 상관)
            ("C_DET", "Concept", 1), ("A", "Concept", 2), ("B", "Concept", 2),
            # C_NOV: 분석 불가 (후행 P·Q 전부 정답 → 분산 0)
            ("C_NOV", "Concept", 1), ("P", "Concept", 2), ("Q", "Concept", 2),
            # C_FEW: 데이터 부족 (후행 M·N 중 M만 데이터)
            ("C_FEW", "Concept", 1), ("M", "Concept", 2), ("N", "Concept", 2),
            # C_STU: 학생 부족 (후행 R·S 공통 학생 2명 < min)
            ("C_STU", "Concept", 1), ("R", "Concept", 2), ("S", "Concept", 2),
        ],
        edges=[
            ("C_DET", "A", "requires"), ("C_DET", "B", "requires"),
            ("C_NOV", "P", "requires"), ("C_NOV", "Q", "requires"),
            ("C_FEW", "M", "requires"), ("C_FEW", "N", "requires"),
            ("C_STU", "R", "requires"), ("C_STU", "S", "requires"),
        ],
    )
    sp = _make_sp_engine(
        tmp_path,
        _records_for_node("A", [1, 1, 1, 0, 0])
        + _records_for_node("B", [0, 0, 0, 1, 1])    # C_DET: 음의 상관
        + _records_for_node("P", [1, 1, 1, 1, 1])
        + _records_for_node("Q", [1, 1, 1, 1, 1])    # C_NOV: 분산 0
        + _records_for_node("M", [1, 0, 1, 0, 1])    # C_FEW: N 없음
        + _records_for_node("R", [1, 0])
        + _records_for_node("S", [0, 1]),            # C_STU: 공통 학생 2명
    )

    out = compute_anomaly_scores(
        SUBJ, min_students=3, min_successors=2, cm_engine=cm, sp_engine=sp
    )

    # 이상 노드는 C_DET 하나만 검출
    assert len(out["anomalies"]) == 1
    detected = out["anomalies"][0]
    assert detected["node_id"] == "C_DET"
    assert detected["anomaly_score"] == pytest.approx(2.0)
    assert detected["sample_students"] == 5

    # 사유별 추출
    summary = out["diagnostics"]["excluded_summary"]
    assert summary["no_variance"] == ["C_NOV"]                    # 분석 불가
    assert summary["insufficient_successor_data"] == ["C_FEW"]    # 데이터 부족
    assert summary["insufficient_common_students"] == ["C_STU"]   # 학생 부족

    # 후보 4개 모두 평가됨, 분류 합이 일치
    assert out["diagnostics"]["candidate_count"] == 4
    excluded_total = sum(len(v) for v in summary.values())
    assert excluded_total == 3
    assert excluded_total + len(out["anomalies"]) == 4


def test_uncomputable_nodes_are_isolated_for_data_reinforcement(tmp_path):
    """분석 불가(no_variance) 노드만 따로 추출 — 데이터 보강 대상 식별 용도."""
    cm = _make_cm_engine(
        tmp_path,
        nodes=[
            ("C_NOV", "Concept", 1), ("P", "Concept", 2), ("Q", "Concept", 2),
            ("C_DET", "Concept", 1), ("A", "Concept", 2), ("B", "Concept", 2),
        ],
        edges=[
            ("C_NOV", "P", "requires"), ("C_NOV", "Q", "requires"),
            ("C_DET", "A", "requires"), ("C_DET", "B", "requires"),
        ],
    )
    sp = _make_sp_engine(
        tmp_path,
        _records_for_node("P", [1, 1, 1, 1, 1])
        + _records_for_node("Q", [1, 1, 1, 1, 1])
        + _records_for_node("A", [1, 1, 0, 0, 1])
        + _records_for_node("B", [0, 0, 1, 1, 0]),
    )

    out = compute_anomaly_scores(
        SUBJ, min_students=3, min_successors=2, cm_engine=cm, sp_engine=sp
    )

    uncomputable = out["diagnostics"]["excluded_summary"]["no_variance"]
    assert uncomputable == ["C_NOV"]
    # 분석 불가 노드는 anomalies에 포함되지 않음
    assert "C_NOV" not in {a["node_id"] for a in out["anomalies"]}
    # 정상 검출 노드는 별개로 존재
    assert "C_DET" in {a["node_id"] for a in out["anomalies"]}


# ── 무변별(degenerate) 노드 = 개념 이상 판정 ──────────────────────────────────
#
# 한 노드에서 모든 학생이 정답(또는 모두 오답)이면 변별력이 없어 개념·문제
# 자체에 이상이 있다고 판단한다. 상관 분석에서는 분산 0으로 제외되지만,
# 별도 degenerate_nodes 로 검출되어야 한다.


def test_degenerate_node_all_correct_flagged(tmp_path):
    """후행 노드가 전 학생 정답(분산 0) → degenerate_nodes로 검출 + 개념 이상 사유."""
    cm = _make_cm_engine(
        tmp_path,
        nodes=[("C1", "Concept", 1), ("X", "Concept", 2), ("Y", "Concept", 2)],
        edges=[("C1", "X", "requires"), ("C1", "Y", "requires")],
    )
    # X·Y 모두 전부 정답 → 상관 분석 불가, 둘 다 무변별
    sp = _make_sp_engine(
        tmp_path,
        _records_for_node("X", [1, 1, 1, 1, 1])
        + _records_for_node("Y", [1, 1, 1, 1, 1]),
    )

    out = compute_anomaly_scores(
        SUBJ, min_students=3, min_successors=2, cm_engine=cm, sp_engine=sp
    )

    # 상관 분석에서는 제외(분산 부족)
    assert out["anomalies"] == []
    assert out["diagnostics"]["excluded_summary"]["no_variance"] == ["C1"]

    # 무변별 노드로 X, Y가 검출됨
    deg = {d["node_id"]: d for d in out["degenerate_nodes"]}
    assert set(deg) == {"X", "Y"}
    assert deg["X"]["correct_rate"] == pytest.approx(1.0)
    assert deg["X"]["reason_code"] == "all_correct"
    assert deg["X"]["sample_students"] == 5
    assert "개념" in deg["X"]["reason"]


def test_degenerate_node_all_incorrect_flagged(tmp_path):
    """후행 노드가 전 학생 오답 → all_incorrect 무변별로 검출."""
    cm = _make_cm_engine(
        tmp_path,
        nodes=[("C1", "Concept", 1), ("X", "Concept", 2), ("Y", "Concept", 2)],
        edges=[("C1", "X", "requires"), ("C1", "Y", "requires")],
    )
    sp = _make_sp_engine(
        tmp_path,
        _records_for_node("X", [0, 0, 0, 0, 0])
        + _records_for_node("Y", [0, 0, 0, 0, 0]),
    )

    out = compute_anomaly_scores(
        SUBJ, min_students=3, min_successors=2, cm_engine=cm, sp_engine=sp
    )

    deg = {d["node_id"]: d for d in out["degenerate_nodes"]}
    assert set(deg) == {"X", "Y"}
    assert deg["X"]["correct_rate"] == pytest.approx(0.0)
    assert deg["X"]["reason_code"] == "all_incorrect"


def test_degenerate_requires_min_students(tmp_path):
    """샘플 학생이 min_students 미만이면 무변별로 판정하지 않음."""
    cm = _make_cm_engine(
        tmp_path,
        nodes=[("C1", "Concept", 1), ("X", "Concept", 2), ("Y", "Concept", 2)],
        edges=[("C1", "X", "requires"), ("C1", "Y", "requires")],
    )
    sp = _make_sp_engine(
        tmp_path,
        _records_for_node("X", [1, 1])      # 2명만 전부 정답
        + _records_for_node("Y", [1, 1]),
    )

    out = compute_anomaly_scores(
        SUBJ, min_students=5, min_successors=2, cm_engine=cm, sp_engine=sp
    )

    assert out["degenerate_nodes"] == []


def test_variant_node_not_degenerate(tmp_path):
    """정답·오답이 섞인 노드는 무변별이 아님."""
    cm = _make_cm_engine(
        tmp_path,
        nodes=[("C1", "Concept", 1), ("X", "Concept", 2), ("Y", "Concept", 2)],
        edges=[("C1", "X", "requires"), ("C1", "Y", "requires")],
    )
    sp = _make_sp_engine(
        tmp_path,
        _records_for_node("X", [1, 1, 1, 0, 0])    # 변별 있음
        + _records_for_node("Y", [1, 1, 1, 1, 1]),  # 전부 정답
    )

    out = compute_anomaly_scores(
        SUBJ, min_students=3, min_successors=2, cm_engine=cm, sp_engine=sp
    )

    deg_ids = {d["node_id"] for d in out["degenerate_nodes"]}
    assert deg_ids == {"Y"}   # X는 변별 있어 제외, Y만 무변별


def test_uncomputable_and_reason_ids_logged(tmp_path, caplog):
    """평가 불가 노드 개수·사유별 id + 무변별 노드가 로그로 남는지 검증."""
    import logging

    cm = _make_cm_engine(
        tmp_path,
        nodes=[("C1", "Concept", 1), ("X", "Concept", 2), ("Y", "Concept", 2)],
        edges=[("C1", "X", "requires"), ("C1", "Y", "requires")],
    )
    sp = _make_sp_engine(
        tmp_path,
        _records_for_node("X", [1, 1, 1, 1, 1])
        + _records_for_node("Y", [1, 1, 1, 1, 1]),
    )

    with caplog.at_level(logging.INFO, logger="services.node_resolution_service"):
        compute_anomaly_scores(
            SUBJ, min_students=3, min_successors=2, cm_engine=cm, sp_engine=sp
        )

    text_log = caplog.text
    # 요약 카운트 로그
    assert "분석불가=1" in text_log
    # 사유별 id 로그
    assert "no_variance) ids=['C1']" in text_log
    # 무변별 노드 경고 로그
    assert "무변별" in text_log
