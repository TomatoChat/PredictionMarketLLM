FROM python:3.14-slim

WORKDIR /app

COPY backend/apis/llm/pyproject.toml ./
RUN pip install --no-cache-dir .

COPY backend/apis/llm/main.py ./
COPY backend/apis/llm/src ./src
COPY backend/shared_models ./shared_models
COPY backend/embedder ./embedder
COPY backend/qdrant ./qdrant
COPY backend/supabase ./supabase
COPY backend/observability ./observability
COPY settings ./settings

ENV PORT=8080
EXPOSE 8080

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8080"]
