from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.schemas.forecast import ForecastRequest, ForecastResponse
from app.services.forecast import calculate_forecast

router = APIRouter(prefix="/api/forecast", tags=["forecast"])


@router.post("", response_model=ForecastResponse)
def post_forecast(payload: ForecastRequest, db: Session = Depends(get_db)) -> dict:
    return calculate_forecast(db, payload)
