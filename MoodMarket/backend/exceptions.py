# c:\Mood_Market\exceptions.py
from datetime import datetime, timezone
from fastapi import Request, status
from fastapi.responses import JSONResponse
import logging

from utils.request_context import get_request_id

logger = logging.getLogger("exceptions")


class MoodMarketException(Exception):
    """Base exception for all MoodMarket API errors."""
    def __init__(self, message: str, status_code: int = status.HTTP_500_INTERNAL_SERVER_ERROR, code: str = "INTERNAL_ERROR"):
        self.message = message
        self.status_code = status_code
        self.code = code
        super().__init__(message)


class AuthException(MoodMarketException):
    """Authentication or Authorization failures."""
    def __init__(self, message: str = "Invalid or missing API key."):
        super().__init__(message, status_code=status.HTTP_401_UNAUTHORIZED, code="UNAUTHORIZED")


class RateLimitException(MoodMarketException):
    """Request rate limit exceeded."""
    def __init__(self, message: str = "Rate limit exceeded. Please try again later."):
        super().__init__(message, status_code=status.HTTP_429_TOO_MANY_REQUESTS, code="TOO_MANY_REQUESTS")


class DatabaseException(MoodMarketException):
    """Database query or connection errors."""
    def __init__(self, message: str = "Database operation failed."):
        super().__init__(message, status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, code="DATABASE_ERROR")


class PredictionNotFoundException(MoodMarketException):
    """Explanation query for a prediction ID that doesn't exist."""
    def __init__(self, prediction_id: str):
        super().__init__(f"Prediction with ID '{prediction_id}' not found.", status_code=status.HTTP_404_NOT_FOUND, code="RESOURCE_NOT_FOUND")


# Custom Exceptions requested
class ModelNotLoadedError(MoodMarketException):
    """Forecasting model is not loaded."""
    def __init__(self, message: str = "The required forecasting model is not loaded."):
        super().__init__(message, status_code=status.HTTP_503_SERVICE_UNAVAILABLE, code="MODEL_NOT_LOADED")


class DatabaseConnectionError(MoodMarketException):
    """Database connection timeout or offline."""
    def __init__(self, message: str = "Database connection timed out or is unavailable."):
        super().__init__(message, status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, code="DATABASE_CONNECTION_ERROR")


class ExternalAPIError(MoodMarketException):
    """Third party API ingestion client exception."""
    def __init__(self, message: str = "External feed ingestion API failed."):
        super().__init__(message, status_code=status.HTTP_502_BAD_GATEWAY, code="EXTERNAL_API_ERROR")


class DataValidationError(MoodMarketException):
    """Validations or schema mismatch failures."""
    def __init__(self, message: str = "Invalid ticker or input data format."):
        super().__init__(message, status_code=status.HTTP_400_BAD_REQUEST, code="INVALID_INPUT")


class PredictionError(MoodMarketException):
    """Forecasting model execution exception."""
    def __init__(self, message: str = "ML Inference failed during prediction execution."):
        super().__init__(message, status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, code="PREDICTION_ERROR")


# Exception handler registrations for FastAPI
def register_exception_handlers(app):
    @app.exception_handler(MoodMarketException)
    async def moodmarket_exception_handler(request: Request, exc: MoodMarketException):
        req_id = get_request_id() or "unknown"
        logger.error(
            f"API Error ({exc.code}) on {request.method} {request.url.path}: {exc.message}",
            extra={"endpoint": request.url.path}
        )
        return JSONResponse(
            status_code=exc.status_code,
            content={
                "error": {
                    "code": exc.code,
                    "message": exc.message,
                    "timestamp": datetime.now(timezone.utc).isoformat() + "Z",
                    "request_id": req_id
                }
            }
        )

    @app.exception_handler(Exception)
    async def global_exception_handler(request: Request, exc: Exception):
        req_id = get_request_id() or "unknown"
        logger.error(
            f"Unhandled system error on {request.method} {request.url.path}: {str(exc)}",
            exc_info=True,
            extra={"endpoint": request.url.path}
        )
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "error": {
                    "code": "INTERNAL_SERVER_ERROR",
                    "message": "Internal server error. Please contact support.",
                    "timestamp": datetime.now(timezone.utc).isoformat() + "Z",
                    "request_id": req_id
                }
            }
        )
