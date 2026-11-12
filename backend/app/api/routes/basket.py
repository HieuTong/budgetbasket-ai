import logging

from fastapi import APIRouter, Depends, Response
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.db.models import User
from app.db.session import get_db
from app.schemas import BasketRequest
from app.services.basket import optimize_for_user

router = APIRouter()
logger = logging.getLogger(__name__)


@router.post("/optimize")
def optimize(
    req: BasketRequest,
    response: Response,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    timings: dict[str, float] = {}
    result = optimize_for_user(db, user.id, req.budget, timings)

    # Server-Timing is a standard header: browsers show it in DevTools (Network -> Timing),
    # so anyone can see where a slow request spends its time without reading server logs.
    response.headers["Server-Timing"] = ", ".join(
        f"{stage};dur={ms:.0f}" for stage, ms in timings.items()
    )
    logger.info(
        "basket optimize user=%s candidates=%s timings_ms=%s",
        user.id,
        result["candidate_count"],
        {stage: round(ms) for stage, ms in timings.items()},
    )
    return result
