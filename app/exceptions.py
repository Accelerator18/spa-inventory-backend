class DomainError(Exception):
    status_code = 400

    def __init__(self, message: str, details: dict | None = None) -> None:
        super().__init__(message)
        self.message = message
        self.details = details or {}


class BadRequestError(DomainError):
    status_code = 400


class NotFoundError(DomainError):
    status_code = 404


class ConflictError(DomainError):
    status_code = 409


class ValidationError(DomainError):
    status_code = 422


class InsufficientStockError(ValidationError):
    def __init__(self, requested_qty: float, available_qty: float) -> None:
        super().__init__(
            "Insufficient stock",
            {
                "requested_qty": round(float(requested_qty), 3),
                "available_qty": round(float(available_qty), 3),
            },
        )
        self.requested_qty = requested_qty
        self.available_qty = available_qty
