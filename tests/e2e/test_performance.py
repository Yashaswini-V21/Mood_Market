import time
import pytest
from fastapi.testclient import TestClient

def test_api_endpoints_latency(client: TestClient):
    """Benchmarks endpoints to verify responses are returned within acceptable latency limits."""
    # Measure Health check latency
    start_time = time.time()
    response = client.get("/api/v1/health")
    elapsed_health = (time.time() - start_time) * 1000
    assert response.status_code == 200
    
    # Measure Sentiment endpoint latency
    start_time = time.time()
    response = client.get("/api/v1/sentiment/AAPL")
    elapsed_sentiment = (time.time() - start_time) * 1000
    assert response.status_code == 200

    # Measure Pipeline endpoint latency
    start_time = time.time()
    response = client.get("/api/v1/pipeline/AAPL")
    elapsed_pipeline = (time.time() - start_time) * 1000
    assert response.status_code == 200

    # Health check: must be near-instant (no DB, no ML)
    assert elapsed_health < 500.0, f"Health check too slow: {elapsed_health:.0f}ms"
    # Sentiment endpoint may hit DB + cache miss: allow up to 3s on dev machine
    assert elapsed_sentiment < 3000.0, f"Sentiment endpoint too slow: {elapsed_sentiment:.0f}ms"
    # Pipeline runs Informer inference on cold cache: allow up to 3s on dev machine
    assert elapsed_pipeline < 3000.0, f"Pipeline endpoint too slow: {elapsed_pipeline:.0f}ms"
