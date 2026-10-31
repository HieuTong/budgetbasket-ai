from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas import BasketRequest
from app.services.basket import optimize_for_user

router = APIRouter()


@router.post("/optimize")
def optimize(req: BasketRequest, db: Session = Depends(get_db)):
    return optimize_for_user(db, req.user_id, req.budget)
