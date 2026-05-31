FROM python:3.14-slim

WORKDIR /app

COPY backend/apis/polymarket/pyproject.toml ./
RUN pip install --no-cache-dir .

COPY backend/apis/polymarket/main.py ./
COPY backend/apis/polymarket/src ./src
COPY backend/shared_models ./shared_models
COPY backend/supabase ./supabase
COPY backend/raw_store ./raw_store
COPY backend/tasks ./tasks
COPY backend/observability ./observability
COPY settings ./settings

ENV PORT=8080
EXPOSE 8080

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8080"]
