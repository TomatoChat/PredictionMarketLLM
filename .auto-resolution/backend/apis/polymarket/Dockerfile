FROM python:3.14-slim

WORKDIR /app

COPY backend/apis/polymarket/pyproject.toml ./
RUN pip install --no-cache-dir .

COPY backend/apis/polymarket/main.py ./
COPY backend/apis/polymarket/src ./src
COPY backend/supabase ./supabase
COPY backend/tasks ./tasks
COPY settings ./settings

# Request models for queues this service produces tasks to.
COPY backend/apis/llm/src/models/EmbedMarketRequest.py ./EmbedMarketRequest.py
COPY backend/apis/llm/src/models/PredictRequest.py ./PredictRequest.py

ENV PORT=8080
EXPOSE 8080

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8080"]
