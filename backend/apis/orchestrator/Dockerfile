FROM python:3.14-slim

WORKDIR /app

COPY backend/apis/orchestrator/pyproject.toml ./
RUN pip install --no-cache-dir .

COPY backend/apis/orchestrator/main.py ./
COPY backend/apis/orchestrator/src ./src
COPY backend/tasks ./tasks
COPY settings ./settings

# Request models for queues this service produces tasks to.
COPY backend/apis/polymarket/src/models/ScrapeRequest.py ./ScrapeRequest.py

ENV PORT=8080
EXPOSE 8080

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8080"]
