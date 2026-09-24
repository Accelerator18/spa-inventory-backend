from pydantic import BaseModel


class AlertOut(BaseModel):
    type: str
    severity: str
    sku: str
    location: str
    message: str
    metrics: dict
