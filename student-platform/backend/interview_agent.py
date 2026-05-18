"""Interview Agent — LLM 기반 질문 생성·답변 평가·진단 리포트."""
import json
import os
from typing import Optional

from openai import OpenAI

MODEL = "gpt-4o"
MAX_TURNS = 15
FOLLOWUP_THRESHOLD = 0.5
MAX_CONSECUTIVE_FOLLOWUPS = 2

_client: Optional[OpenAI] = None


def _get_client() -> OpenAI:
    global _client
    if _client is None:
        _client = OpenAI(api_key=os.environ["OPENAI_API_KEY"])
    return _client


def _chat(system: str, user: str, max_tokens: int = 500) -> str:
    response = _get_client().chat.completions.create(
        model=MODEL,
        max_tokens=max_tokens,
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
    )
    return response.choices[0].message.content.strip()


# ── EMA ──────────────────────────────────────────────────────────────────────

def apply_ema(current: float, score: float, alpha: float = 0.3) -> float:
    return round(alpha * score + (1 - alpha) * current, 4)


# ── 타겟 선택 ─────────────────────────────────────────────────────────────────

def select_target_nodes(
    working_mastery: dict[str, float],
    nodes: list[dict],
    covered_node_ids: set[str],
    last_score: Optional[float],
    consecutive_followups: int,
    current_target_nodes: Optional[list[str]],
) -> tuple[list[str], str]:
    """다음 질문 대상 노드와 액션(follow_up | pivot)을 결정한다."""

    if (
        last_score is not None
        and last_score < FOLLOWUP_THRESHOLD
        and consecutive_followups < MAX_CONSECUTIVE_FOLLOWUPS
        and current_target_nodes
    ):
        return current_target_nodes, "follow_up"

    uncovered = [n for n in nodes if n["id"] not in covered_node_ids]
    candidates = sorted(
        uncovered or nodes,
        key=lambda n: working_mastery.get(n["id"], 0.5),
    )

    if not candidates:
        return [], "pivot"

    return [candidates[0]["id"]], "pivot"


# ── 질문 생성 ─────────────────────────────────────────────────────────────────

def generate_question(
    subject_name: str,
    target_nodes: list[dict],
    conversation_history: list[dict],
    action: str,
    mastery_level: float,
) -> str:
    """대상 노드에 대한 인터뷰 질문을 동적으로 생성한다."""

    node_desc = "\n".join(
        f"- {n.get('name', n['id'])}: {n.get('description', '')}" for n in target_nodes
    )
    history_text = _format_history(conversation_history)
    mastery_label = _mastery_label(mastery_level)

    instruction = (
        "The student's previous answer was incomplete or shallow. "
        "Ask a targeted follow-up question that probes the specific gap. Do NOT repeat the same question."
        if action == "follow_up"
        else
        "Start a new line of questioning on the concepts below. "
        "Ask an open-ended question appropriate for the student's current level."
    )

    system = (
        "You are an expert technical interviewer conducting a knowledge assessment. "
        "Ask one clear, focused question per turn. Keep it concise (1-3 sentences). "
        "No hints or answers. Respond with only the question text."
    )

    user_parts = [
        f"Subject: {subject_name}",
        f"Target concepts:\n{node_desc}",
        f"Student mastery level: {mastery_label} ({mastery_level:.2f})",
        f"Instruction: {instruction}",
    ]
    if history_text:
        user_parts.append(f"Conversation so far:\n{history_text}")

    return _chat(system, "\n\n".join(user_parts), max_tokens=300)


# ── 답변 평가 ─────────────────────────────────────────────────────────────────

def evaluate_answer(
    question: str,
    answer: str,
    target_nodes: list[dict],
    subject_name: str,
) -> dict:
    """학생 답변을 평가하여 score, feedback, demonstrated_concepts를 반환한다."""

    node_desc = "\n".join(
        f"- {n.get('name', n['id'])}: {n.get('description', '')}" for n in target_nodes
    )

    system = (
        "You are an expert educational evaluator. "
        "Evaluate the student's answer and respond ONLY with a JSON object — no markdown."
    )

    user = f"""Subject: {subject_name}
Concepts being tested:
{node_desc}

Question: {question}

Student's answer: {answer}

Return JSON:
{{
  "score": <float 0.0-1.0>,
  "feedback": "<2-3 sentence feedback in Korean>",
  "demonstrated_concepts": ["<concept name>", ...]
}}"""

    raw = _chat(system, user, max_tokens=500)
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        return {"score": 0.5, "feedback": raw[:300], "demonstrated_concepts": []}


# ── 진단 리포트 ───────────────────────────────────────────────────────────────

def generate_diagnosis(
    subject_name: str,
    nodes: list[dict],
    turns: list[dict],
    final_mastery: dict[str, float],
    assessed_node_ids: set[str],
) -> dict:
    """세션 전체를 분석하여 최종 진단 리포트를 생성한다.

    assessed_node_ids: 실제 인터뷰에서 질문이 나간 노드 ID 집합.
    미방문 노드는 strengths/weaknesses 대신 not_covered로 분리한다.
    """
    node_map = {n["id"]: n.get("name", n["id"]) for n in nodes}

    assessed_nodes = [n for n in nodes if n["id"] in assessed_node_ids]
    not_covered_nodes = [n for n in nodes if n["id"] not in assessed_node_ids]

    assessed_summary = "\n".join(
        f"- {n.get('name', n['id'])}: {final_mastery.get(n['id'], 0.5):.2f}"
        for n in assessed_nodes
    )
    turns_summary = "\n".join(
        f"Turn {t['turn_number']}: score={t['score']:.2f} | Q={t['question'][:80]}..."
        for t in turns
    )

    system = (
        "You are an expert educational diagnostician. "
        "Analyze the interview and produce a final diagnosis. "
        "Respond ONLY with a JSON object — no markdown."
    )

    user = f"""Subject: {subject_name}

Assessed nodes (actually questioned during interview) with final mastery:
{assessed_summary or "(none)"}

Interview turns:
{turns_summary or "(none)"}

Return JSON evaluating ONLY the assessed nodes above:
{{
  "overall_band": "<S|A|B|C|D based on assessed nodes: S>=0.9, A>=0.75, B>=0.6, C>=0.45, D<0.45>",
  "strengths": ["<assessed node name where mastery >= 0.7>", ...],
  "weaknesses": ["<assessed node name where mastery < 0.6>", ...],
  "recommendations": ["<specific next learning action in Korean>", ...]
}}"""

    raw = _chat(system, user, max_tokens=800)
    try:
        result = json.loads(raw)
    except json.JSONDecodeError:
        avg = (
            sum(final_mastery.get(nid, 0.5) for nid in assessed_node_ids) / len(assessed_node_ids)
            if assessed_node_ids else 0.5
        )
        result = {
            "overall_band": _band(avg),
            "strengths": [],
            "weaknesses": [],
            "recommendations": ["학습을 계속하세요."],
        }

    result["not_covered"] = [node_map[n["id"]] for n in not_covered_nodes]
    return result


# ── 헬퍼 ──────────────────────────────────────────────────────────────────────

def _format_history(history: list[dict]) -> str:
    lines = []
    for h in history[-6:]:
        lines.append(f"Q: {h['question']}")
        lines.append(f"A: {h['answer']} (score: {h['score']:.2f})")
    return "\n".join(lines)


def _mastery_label(score: float) -> str:
    if score >= 0.8:
        return "advanced"
    if score >= 0.6:
        return "intermediate"
    if score >= 0.4:
        return "beginner"
    return "novice"


def _band(avg: float) -> str:
    if avg >= 0.9:
        return "S"
    if avg >= 0.75:
        return "A"
    if avg >= 0.6:
        return "B"
    if avg >= 0.45:
        return "C"
    return "D"
