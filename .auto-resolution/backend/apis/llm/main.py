from fastapi import FastAPI

from src.routes import embed_market, health, predict, ready

app = FastAPI(title="llm")
app.include_router(health.router)
app.include_router(ready.router)
app.include_router(predict.router)
app.include_router(embed_market.router)
