from datetime import datetime

DEFAULT_FEATURES = [
    {
        "key": "prior_knowledge_level",
        "display_name": "사전 지식 수준",
        "description": (
            "해당 subject에 대한 학습 시작 전 지식 수준. "
            "0.0은 완전 초보, 1.0은 전문가 수준."
        ),
        "value_type": "numeric",
        "value_options": None,
        "value_range": {"min": 0.0, "max": 1.0},
        "default_value": "0.5",
        "category": "숙련도",
        "is_builtin": True,
        "created_at": datetime.utcnow(),
    },
    {
        "key": "conceptual_depth",
        "display_name": "개념 이해 깊이",
        "description": (
            "개념을 표면적으로 암기하는지, 원리까지 이해하는지를 나타낸다. "
            "표면적은 정의 암기 수준, 깊은은 응용·연결이 가능한 수준."
        ),
        "value_type": "categorical",
        "value_options": ["표면적", "보통", "깊은"],
        "value_range": None,
        "default_value": "보통",
        "category": "숙련도",
        "is_builtin": True,
        "created_at": datetime.utcnow(),
    },
    {
        "key": "learning_pace",
        "display_name": "학습 속도",
        "description": (
            "새로운 개념을 습득하는 속도. "
            "느린 학습자는 반복이 필요하고, 빠른 학습자는 적은 노출로 습득한다."
        ),
        "value_type": "categorical",
        "value_options": ["느린", "보통", "빠른"],
        "value_range": None,
        "default_value": "보통",
        "category": "학습특성",
        "is_builtin": True,
        "created_at": datetime.utcnow(),
    },
    {
        "key": "error_pattern",
        "display_name": "오류 패턴",
        "description": (
            "이 학생이 주로 범하는 오류 유형에 대한 자유 텍스트 설명. "
            "예: '절차를 건너뜀', '개념을 혼동함', '계산 실수가 잦음'."
        ),
        "value_type": "text",
        "value_options": None,
        "value_range": None,
        "default_value": "특이 패턴 없음",
        "category": "학습특성",
        "is_builtin": True,
        "created_at": datetime.utcnow(),
    },
    {
        "key": "question_interpretation_accuracy",
        "display_name": "문제 해석 정확도",
        "description": (
            "문제 지문을 출제자의 의도대로 정확히 해석하는 정도. "
            "0.0은 자주 잘못 해석, 1.0은 항상 정확히 해석."
        ),
        "value_type": "numeric",
        "value_options": None,
        "value_range": {"min": 0.0, "max": 1.0},
        "default_value": "0.7",
        "category": "학습특성",
        "is_builtin": True,
        "created_at": datetime.utcnow(),
    },
    {
        "key": "confidence_level",
        "display_name": "자신감 수준",
        "description": (
            "자신의 답변에 대한 자신감 경향. "
            "과신은 틀려도 확신하고, 낮음은 맞아도 불확실하게 표현한다."
        ),
        "value_type": "categorical",
        "value_options": ["낮음", "보통", "높음", "과신"],
        "value_range": None,
        "default_value": "보통",
        "category": "기질",
        "is_builtin": True,
        "created_at": datetime.utcnow(),
    },
    {
        "key": "persistence",
        "display_name": "끈기",
        "description": (
            "어려운 문제에서 포기하지 않고 계속 시도하는 정도. "
            "0.0은 조금만 막혀도 포기, 1.0은 끝까지 시도."
        ),
        "value_type": "numeric",
        "value_options": None,
        "value_range": {"min": 0.0, "max": 1.0},
        "default_value": "0.5",
        "category": "기질",
        "is_builtin": True,
        "created_at": datetime.utcnow(),
    },
    {
        "key": "risk_tolerance",
        "display_name": "위험 감수 성향",
        "description": (
            "불확실한 상황에서 추측 답변을 제출하는 의향. "
            "낮음은 모르면 빈칸, 높음은 추측해서라도 제출."
        ),
        "value_type": "categorical",
        "value_options": ["낮음", "보통", "높음"],
        "value_range": None,
        "default_value": "보통",
        "category": "기질",
        "is_builtin": True,
        "created_at": datetime.utcnow(),
    },
    {
        "key": "verbosity",
        "display_name": "답변 상세도",
        "description": (
            "답변 작성 시 설명의 길이와 상세함 정도. "
            "간략은 핵심만, 장문은 배경·근거까지 상세히 서술."
        ),
        "value_type": "categorical",
        "value_options": ["간략", "보통", "장문"],
        "value_range": None,
        "default_value": "보통",
        "category": "답변 행동",
        "is_builtin": True,
        "created_at": datetime.utcnow(),
    },
    {
        "key": "reasoning_style",
        "display_name": "추론 스타일",
        "description": (
            "문제를 풀 때 사용하는 추론 방식. "
            "직관적은 빠른 휴리스틱, 단계적은 절차 준수, 분석적은 분해 후 합성."
        ),
        "value_type": "categorical",
        "value_options": ["직관적", "단계적", "분석적"],
        "value_range": None,
        "default_value": "단계적",
        "category": "답변 행동",
        "is_builtin": True,
        "created_at": datetime.utcnow(),
    },
]
