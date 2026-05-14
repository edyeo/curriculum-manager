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

# 기본값: curriculum-manager
ENV AGENT=curriculum-manager
ENV PORT=8001

# 헬스 체크
HEALTHCHECK --interval=10s --timeout=5s --retries=3 \
    CMD curl -f http://localhost:${PORT}/health || exit 1

CMD python -m apps.${AGENT}.main
