from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.schemas.alert import AlertOut
from app.services.alerts import get_alerts

router = APIRouter(prefix="/api/alerts", tags=["alerts"])


@router.get("", response_model=list[AlertOut])
def list_alerts(
    location: str | None = None,
    type: str | None = Query(default=None),
    severity: str | None = None,
    db: Session = Depends(get_db),
) -> list[dict]:
    return get_alerts(db, location=location, alert_type=type, severity=severity)
