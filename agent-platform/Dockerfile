FROM python:3.12-slim

WORKDIR /app

# 시스템 패키지 설치
RUN apt-get update && apt-get install -y \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Python 의존성 설치
COPY pyproject.toml .
RUN pip install --no-cache-dir -e .

# 코드 복사
COPY . .

# agents/ 패키지 초기화 + 하이픈→언더스코어 심볼릭 링크
RUN touch /app/agents/__init__.py && \
    ln -sf /app/agents/curriculum-manager /app/agents/curriculum_manager && \
    ln -sf /app/agents/mental-model-manager /app/agents/mental_model_manager && \
    ln -sf /app/agents/question-generator /app/agents/question_generator && \
    ln -sf /app/agents/virtual-student /app/agents/virtual_student && \
    chmod +x /app/entrypoint.sh

# 기본값: curriculum-manager
ENV AGENT=curriculum-manager
ENV PORT=8001
ENV PYTHONPATH=/app

# 헬스 체크
HEALTHCHECK --interval=10s --timeout=5s --retries=3 \
    CMD curl -f http://localhost:${PORT}/health || exit 1

ENTRYPOINT ["/app/entrypoint.sh"]
