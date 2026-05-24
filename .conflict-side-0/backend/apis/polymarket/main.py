from fastapi import FastAPI

from src.routes import health, markets, ready, scrape

app = FastAPI(title="polymarket")
app.include_router(health.router)
app.include_router(ready.router)
app.include_router(markets.router)
app.include_router(scrape.router)
