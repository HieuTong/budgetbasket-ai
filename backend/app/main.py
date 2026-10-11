import logging
import os
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text

from app.api.routes import (
    basket,
    catalog,
    chat,
    decision,
    price_intelligence,
    purchases,
    similarity,
)
from app.api.routes.purchase_profile import router as purchase_profile_router
from app.core.config import settings
from app.db.session import engine
from app.services.opensearch_catalog import create_client

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage the shared OpenSearch client for the application lifecycle."""
    backend = os.getenv("PRODUCT_SEARCH_BACKEND", "legacy").strip().lower()
    app.state.opensearch_client = None

    if backend not in {"legacy", "opensearch"}:
        raise RuntimeError(
            "Unsupported PRODUCT_SEARCH_BACKEND. Use 'legacy' or 'opensearch'."
        )

    try:
        if backend == "opensearch":
            app.state.opensearch_client = create_client()

        yield
    finally:
        client = app.state.opensearch_client
        app.state.opensearch_client = None

        if client is not None:
            try:
                client.close()
            except Exception:
                logger.exception("Failed to close the OpenSearch client")


app = FastAPI(
    title="BudgetBasket AI",
    description=(
        "Cost-of-living optimizer: ML + RAG + Agentic AI "
        "over your purchase history and budget."
    ),
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
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


app.include_router(catalog.router)
app.include_router(purchases.router)
app.include_router(basket.router)
app.include_router(chat.router)
app.include_router(purchase_profile_router)
app.include_router(price_intelligence.router)
app.include_router(similarity.router)
app.include_router(decision.router)


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
