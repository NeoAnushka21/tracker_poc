"""Quick water buttons on the dashboard. These are the user's own clicks, so they save
directly; water mentioned in chat still goes through a confirmation card."""
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.config import WATER_MAX_LOG_ML
from app.db import get_db
from app.deps import onboarded_user
from app.models import User, WaterLog
from app.services.water import add_water

router = APIRouter(prefix="/api/water", tags=["water"])


class WaterIn(BaseModel):
    amount_ml: float = Field(gt=0, le=WATER_MAX_LOG_ML)


@router.post("", status_code=status.HTTP_201_CREATED)
def log_water(body: WaterIn, user: User = Depends(onboarded_user), db: Session = Depends(get_db)):
    log = add_water(db, user, body.amount_ml)
    db.commit()
    return {"id": log.id, "amount_ml": log.amount_ml}


@router.delete("/{water_id}")
def delete_water(water_id: int, user: User = Depends(onboarded_user), db: Session = Depends(get_db)):
    log = db.get(WaterLog, water_id)
    if log is None or log.user_id != user.id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Water log not found")
    db.delete(log)
    db.commit()
    return {"ok": True}
