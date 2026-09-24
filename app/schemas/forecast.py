from datetime import date

from pydantic import BaseModel, Field, model_validator


class ForecastRequest(BaseModel):
    sku: str = Field(min_length=1, max_length=32)
    location: str = Field(min_length=1, max_length=32)
    horizon_days: int | None = Field(default=None, ge=1, le=3650)
    horizon_months: int | None = Field(default=None, ge=1, le=24)
    safety_stock_days: int | None = Field(default=None, ge=0, le=365)

    @model_validator(mode="after")
    def validate_horizon(self) -> "ForecastRequest":
        if (self.horizon_days is None) == (self.horizon_months is None):
            raise ValueError("Specify exactly one of horizon_days or horizon_months")
        return self


class ForecastPeriod(BaseModel):
    from_date: date
    to_date: date
    days: int


class ForecastExplanation(BaseModel):
    data_used: list[str]
    period: str
    formulas: list[str]
    assumptions: list[str]
    as_of: date


class ForecastWarning(BaseModel):
    level: str
    message: str


class ForecastResponse(BaseModel):
    sku: str
    name: str
    unit: str
    location: str
    period: dict
    avg_daily_consumption: float
    forecast_demand: float
    current_stock: float
    incoming_qty: float
    safety_stock: float
    reorder_point: float
    recommended_purchase_qty: float
    unit_price: float
    estimated_cost: float
    recommended_order_date: date | None
    stockout_date: date | None
    explanation: ForecastExplanation
    warnings: list[ForecastWarning]
