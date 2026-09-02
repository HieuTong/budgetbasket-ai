from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import basket, chat, purchases
from app.core.config import settings

app = FastAPI(
    title="BudgetBasket AI",
    description="Cost-of-living optimizer: ML + RAG + Agentic AI over your purchase history and budget.",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(purchases.router, prefix="/api/purchases", tags=["purchases"])
app.include_router(basket.router, prefix="/api/basket", tags=["basket"])
app.include_router(chat.router, prefix="/api/chat", tags=["agent"])


@app.get("/health")
def health():
    return {"status": "ok"}
