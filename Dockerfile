FROM python:3.11-slim

WORKDIR /app

COPY requirements-api.txt .
RUN pip install --no-cache-dir -r requirements-api.txt

COPY app.py .
COPY src/ src/
COPY data/processed/ data/processed/
COPY data/reference/ data/reference/
COPY web/mock/ web/mock/
COPY demo_fixtures/ demo_fixtures/
COPY docs/results/img/ docs/results/img/
COPY docs/w1b_data_status.csv docs/w1b_data_status.csv
COPY docs/results/w3_metrics.json docs/results/w3_metrics.json

EXPOSE 7860

CMD ["/bin/sh", "-c", "exec uvicorn app:app --host 0.0.0.0 --port ${PORT:-7860}"]
