FROM python:3.12-slim

RUN apt-get update && apt-get install -y curl && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
RUN pip install "bcrypt==4.2.1" -q

COPY . .

ENV PYTHONPATH=/app

HEALTHCHECK --interval=10s --timeout=5s --retries=3 \
    CMD curl -f http://localhost:8010/api/health || exit 1

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8010"]
