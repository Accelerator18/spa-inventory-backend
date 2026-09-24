from datetime import date, timedelta

from sqlalchemy.orm import Session

from app.calculations.forecast import build_forecast_period, estimate_stockout_date
from app.calculations.inventory import (
    average_daily_consumption,
    calculate_estimated_cost,
    calculate_reorder_point,
    calculate_safety_stock,
    raw_recommended_qty,
    round_recommended_qty,
)
from app.exceptions import NotFoundError
from app.models import Location, Product
from app.schemas.forecast import ForecastRequest
from app.services.inventory import (
    get_consumption_total,
    get_incoming_orders,
    get_latest_unit_price,
    get_total_stock,
)


def calculate_forecast(db: Session, payload: ForecastRequest) -> dict:
    product = db.get(Product, payload.sku)
    if product is None:
        raise NotFoundError(f"Unknown SKU: {payload.sku}")
    if db.get(Location, payload.location) is None:
        raise NotFoundError(f"Unknown location: {payload.location}")

    as_of = date.today()
    period_from, period_to, period_days = build_forecast_period(as_of, payload.horizon_days, payload.horizon_months)
    consumption_total = get_consumption_total(db, payload.sku, payload.location, as_of, 90)
    avg_daily = average_daily_consumption(consumption_total, 90)
    current_stock = get_total_stock(db, payload.sku, payload.location)
    orders_in_period = get_incoming_orders(db, payload.sku, payload.location, as_of, period_to)
    incoming_qty = round(sum(float(order.qty) for order in orders_in_period), 3)

    safety_days = payload.safety_stock_days if payload.safety_stock_days is not None else product.safety_stock_days
    forecast_demand = round(avg_daily * period_days, 3)
    safety_stock = calculate_safety_stock(avg_daily, safety_days)
    reorder_point = calculate_reorder_point(avg_daily, product.lead_time_days, safety_days)
    raw_qty = raw_recommended_qty(forecast_demand, safety_stock, current_stock, incoming_qty)
    recommended_qty = round_recommended_qty(raw_qty, float(product.pack_size), float(product.min_order_qty))
    unit_price = get_latest_unit_price(db, payload.sku, payload.location) or float(product.default_price)
    estimated_cost = calculate_estimated_cost(recommended_qty, unit_price)

    all_open_orders = get_incoming_orders(db, payload.sku, payload.location, as_of)
    stockout_date = estimate_stockout_date(
        as_of,
        current_stock,
        avg_daily,
        [(order.expected_delivery_date, float(order.qty)) for order in all_open_orders],
    )
    recommended_order_date = None
    if stockout_date is not None:
        recommended_order_date = max(as_of, stockout_date - timedelta(days=product.lead_time_days))

    warnings: list[dict] = []
    if current_stock < reorder_point - 1e-9:
        warnings.append({"level": "warning", "message": "Current stock is below reorder point"})
    if stockout_date is not None and stockout_date <= as_of + timedelta(days=product.lead_time_days):
        warnings.append({"level": "critical", "message": "Stock may run out before the regular supplier lead time"})
    if avg_daily == 0:
        warnings.append({"level": "info", "message": "No consumption in the last 90 days; purchase recommendation is zero unless safety stock requires otherwise"})

    return {
        "sku": product.sku,
        "name": product.name,
        "unit": product.unit,
        "location": payload.location,
        "period": {"from": period_from, "to": period_to, "days": period_days},
        "avg_daily_consumption": avg_daily,
        "forecast_demand": forecast_demand,
        "current_stock": current_stock,
        "incoming_qty": incoming_qty,
        "safety_stock": safety_stock,
        "reorder_point": reorder_point,
        "recommended_purchase_qty": recommended_qty,
        "unit_price": round(unit_price, 2),
        "estimated_cost": estimated_cost,
        "recommended_order_date": recommended_order_date,
        "stockout_date": stockout_date,
        "explanation": {
            "data_used": [
                "Consumption movements for the last 90 days",
                f"Stock reconstructed from movements as of {as_of.isoformat()}",
                "Open supplier orders with expected delivery dates",
                "Product pack size, minimum order and lead time",
            ],
            "period": f"{period_from.isoformat()} — {period_to.isoformat()} ({period_days} days)",
            "formulas": [
                "avg_daily_consumption = consume qty for 90 days / 90",
                "forecast_demand = avg_daily_consumption * period_days",
                "safety_stock = avg_daily_consumption * safety_stock_days",
                "reorder_point = avg_daily_consumption * lead_time_days + safety_stock",
                "purchase = forecast_demand + safety_stock - current_stock - incoming_qty",
                "recommended qty is rounded upward to package size and supplier minimum order",
            ],
            "assumptions": [
                "For horizon_months the forecast covers the next N full calendar months.",
                "Unit price is the latest receipt price for the location; product default price is the fallback.",
                "Only open orders with status ordered/confirmed/delayed are counted as incoming.",
            ],
            "as_of": as_of,
        },
        "warnings": warnings,
    }
