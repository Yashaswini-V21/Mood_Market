import pytest
from fastapi.testclient import TestClient

def test_user_journey_flow(client: TestClient):
    """Simulates an end-to-end user session navigating the dashboard."""
    # 1. User checks application health
    health_response = client.get("/api/v1/health")
    assert health_response.status_code == 200
    assert health_response.json()["status"] in ["healthy", "degraded"]

    # 2. User searches ticker sentiment
    sentiment_response = client.get("/api/v1/sentiment/AAPL")
    assert sentiment_response.status_code == 200
    sentiment_data = sentiment_response.json()
    assert "sentiment" in sentiment_data

    # 3. User checks forecast for same ticker
    forecast_response = client.get("/api/v1/price/forecast/AAPL")
    assert forecast_response.status_code == 200
    forecast_data = forecast_response.json()
    assert "direction" in forecast_data

    # 4. User queries full pipeline breakdown
    pipeline_response = client.get("/api/v1/pipeline/AAPL")
    assert pipeline_response.status_code == 200
    pipeline_data = pipeline_response.json()
    assert "risk" in pipeline_data

