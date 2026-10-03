import logging

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text

from app.api.routes import (
    basket,
    catalog,
    chat,
    purchases,
    price_intelligence,
    decision,
    similarity,
)
from app.api.routes.purchase_profile import router as purchase_profile_router
from app.core.config import settings
from app.db.session import engine


logger = logging.getLogger(__name__)


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

app.include_router(
    catalog.router,
    prefix="/api/catalog",
    tags=["catalog"],
)

app.include_router(
    purchases.router,
    prefix="/api/purchases",
    tags=["purchases"],
)

app.include_router(
    basket.router,
    prefix="/api/basket",
    tags=["basket"],
)

app.include_router(
    chat.router,
    prefix="/api/chat",
    tags=["agent"],
)

app.include_router(
    purchase_profile_router,
    prefix="/api",
)

app.include_router(
    price_intelligence.router,
    prefix="/api",
)

app.include_router(
    similarity.router,
    prefix="/api",
)

app.include_router(
    decision.router,
    prefix="/api",
)


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/ready")
def readiness():
    try:
        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))
    except Exception as exc:
        logger.exception("Database readiness check failed")
        raise HTTPException(
            status_code=503,
            detail="database_unavailable",
        ) from exc

    return {"status": "ready"}
