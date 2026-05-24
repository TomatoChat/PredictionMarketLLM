from fastapi import FastAPI

from src.routes import health, prepare_scraping, ready

app = FastAPI(title="orchestrator")
app.include_router(health.router)
app.include_router(ready.router)
app.include_router(prepare_scraping.router)
