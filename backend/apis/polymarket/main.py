from fastapi import FastAPI
from observability import configure_observability
from settings import get_settings

from src.routes import health, ready, scrape

app = FastAPI(title="polymarket")
configure_observability(
    app=app,
    service_name="polymarket",
    project_id=get_settings().GCP_PROJECT_ID,
)
app.include_router(health.router)
app.include_router(ready.router)
app.include_router(scrape.router)
