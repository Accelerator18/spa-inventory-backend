from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from app.api.alerts import router as alerts_router
from app.api.forecast import router as forecast_router
from app.api.movements import router as movements_router
from app.api.stock import router as stock_router
from app.config import settings
from app.exceptions import DomainError

app = FastAPI(title=settings.app_name, version=settings.app_version)


@app.exception_handler(DomainError)
async def domain_error_handler(_: Request, exc: DomainError) -> JSONResponse:
    payload = {"message": exc.message}
    if exc.details:
        payload.update(exc.details)
    return JSONResponse(status_code=exc.status_code, content={"detail": payload})


@app.get("/health", tags=["system"])
def health() -> dict:
    return {"status": "ok", "version": settings.app_version}


app.include_router(movements_router)
app.include_router(stock_router)
app.include_router(forecast_router)
app.include_router(alerts_router)
