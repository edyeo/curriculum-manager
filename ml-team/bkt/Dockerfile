FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# bkt_model.py — serving/model_store.py가 상위 경로에서 import
COPY bkt_model.py .
COPY serving/ serving/

ENV PORT=8007
EXPOSE 8007

CMD ["python", "serving/main.py"]
