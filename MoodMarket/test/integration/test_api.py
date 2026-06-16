import pytest
from fastapi.testclient import TestClient

def test_health_check(client: TestClient):
    """Test health check route."""
    response = client.get("/api/v1/health")
    assert response.status_code == 200
    data = response.json()
    assert "status" in data
    assert "models_loaded" in data
    assert "db_connected" in data

def test_sentiment_endpoint(client: TestClient):
    """Test GET /api/v1/sentiment/{ticker}."""
    response = client.get("/api/v1/sentiment/AAPL")
    assert response.status_code == 200
    data = response.json()
    assert "sentiment" in data
    assert "confidence" in data
    assert "updated_at" in data
    assert -1.0 <= data["sentiment"] <= 1.0
    assert 0.0 <= data["confidence"] <= 1.0

def test_forecast_endpoint(client: TestClient):
    """Test GET /api/v1/price/forecast/{ticker}."""
    response = client.get("/api/v1/price/forecast/AAPL")
    assert response.status_code == 200
    data = response.json()
    assert "prediction" in data
    assert "confidence" in data
    assert "direction" in data
    assert "timeframe" in data

def test_pipeline_endpoint(client: TestClient):
    """Test GET /api/v1/pipeline/{ticker}."""
    response = client.get("/api/v1/pipeline/AAPL")
    assert response.status_code == 200
    data = response.json()
    assert "sentiment" in data
    assert "price_forecast" in data
    assert "risk" in data
    assert "timestamp" in data


# clean architecture alignment
