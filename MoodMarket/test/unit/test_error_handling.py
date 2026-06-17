# c:\Mood_Market\tests\test_error_handling.py
import os
import sys
import json
import logging
import unittest
from unittest.mock import MagicMock
from datetime import datetime
from fastapi import FastAPI
from fastapi.testclient import TestClient

# Add project root directory to path to resolve imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from logging_config import JSONFormatter
from utils.request_context import set_request_id, set_user_id, clear_context
from exceptions import (
    register_exception_handlers,
    ModelNotLoadedError,
    DatabaseConnectionError,
    ExternalAPIError,
    DataValidationError,
    PredictionError
)


class TestErrorHandlingAndLogging(unittest.TestCase):
    """Verifies custom error handlers, JSON logs schema, context IDs, and PII filters."""

    def setUp(self):
        clear_context()

    def tearDown(self):
        clear_context()

    def test_json_formatter_metadata(self):
        # Setup context IDs
        set_request_id("req_12345")
        set_user_id("user_abc")
        
        formatter = JSONFormatter()
        log_record = logging.LogRecord(
            name="api.logger",
            level=logging.INFO,
            pathname="test_file.py",
            lineno=42,
            msg="Successful stock forecast check.",
            args=(),
            exc_info=None
        )
        
        log_output = formatter.format(log_record)
        log_json = json.loads(log_output)
        
        # Verify JSON keys
        self.assertEqual(log_json["level"], "INFO")
        self.assertEqual(log_json["logger_name"], "api.logger")
        self.assertEqual(log_json["message"], "Successful stock forecast check.")
        self.assertEqual(log_json["request_id"], "req_12345")
        self.assertEqual(log_json["user_id"], "user_abc")
        self.assertTrue("timestamp" in log_json)

    def test_pii_and_credential_masking(self):
        formatter = JSONFormatter()
        
        # Test masking in string messages
        log_record_msg = logging.LogRecord(
            name="api.logger",
            level=logging.WARNING,
            pathname="test_file.py",
            lineno=42,
            msg="Failed auth with credentials: password=supersecret123 and api_key=moodmarket_key",
            args=(),
            exc_info=None
        )
        
        log_output = formatter.format(log_record_msg)
        log_json = json.loads(log_output)
        self.assertIn("[MASKED]", log_json["message"])
        self.assertNotIn("supersecret123", log_json["message"])
        self.assertNotIn("moodmarket_key", log_json["message"])

        # Test masking in extra context dictionary
        log_record_ctx = logging.LogRecord(
            name="api.logger",
            level=logging.INFO,
            pathname="test_file.py",
            lineno=42,
            msg="Request metrics",
            args=(),
            exc_info=None
        )
        log_record_ctx.context = {
            "api_key": "raw_secret_api_key",
            "normal_field": "AAPL"
        }
        
        log_output = formatter.format(log_record_ctx)
        log_json = json.loads(log_output)
        self.assertEqual(log_json["context"]["api_key"], "[MASKED]")
        self.assertEqual(log_json["context"]["normal_field"], "AAPL")

    def test_custom_exception_handlers(self):
        # Create a mock FastAPI app with registration
        app = FastAPI()
        register_exception_handlers(app)
        
        # Define routes raising our custom exceptions
        @app.get("/error/model")
        def route_model():
            raise ModelNotLoadedError("Model weight file best_model.pt not loaded.")

        @app.get("/error/db")
        def route_db():
            raise DatabaseConnectionError("TimescaleDB connection failed.")

        @app.get("/error/api")
        def route_api():
            raise ExternalAPIError("Reddit API returned 503 Service Unavailable.")

        @app.get("/error/validation")
        def route_validation():
            raise DataValidationError("Stock ticker must be 1-4 characters.")

        @app.get("/error/prediction")
        def route_prediction():
            raise PredictionError("Informer model crashed on prediction batch.")

        client = TestClient(app)
        set_request_id("req_exception_123")

        # 1. Test ModelNotLoadedError (503)
        res = client.get("/error/model")
        self.assertEqual(res.status_code, 503)
        body = res.json()
        self.assertEqual(body["error"]["code"], "MODEL_NOT_LOADED")
        self.assertEqual(body["error"]["request_id"], "req_exception_123")

        # 2. Test DatabaseConnectionError (500)
        res = client.get("/error/db")
        self.assertEqual(res.status_code, 500)
        body = res.json()
        self.assertEqual(body["error"]["code"], "DATABASE_CONNECTION_ERROR")

        # 3. Test ExternalAPIError (502)
        res = client.get("/error/api")
        self.assertEqual(res.status_code, 502)
        body = res.json()
        self.assertEqual(body["error"]["code"], "EXTERNAL_API_ERROR")

        # 4. Test DataValidationError (400)
        res = client.get("/error/validation")
        self.assertEqual(res.status_code, 400)
        body = res.json()
        self.assertEqual(body["error"]["code"], "INVALID_INPUT")

        # 5. Test PredictionError (500)
        res = client.get("/error/prediction")
        self.assertEqual(res.status_code, 500)
        body = res.json()
        self.assertEqual(body["error"]["code"], "PREDICTION_ERROR")


if __name__ == "__main__":
    unittest.main()
