from fastapi import FastAPI
from observability import configure_observability
from settings import get_settings

from src.routes import embed_market, health, predict, ready

app = FastAPI(title="llm")
configure_observability(
    app=app,
    service_name="llm",
    project_id=get_settings().GCP_PROJECT_ID,
)
app.include_router(health.router)
app.include_router(ready.router)
app.include_router(predict.router)
app.include_router(embed_market.router)
