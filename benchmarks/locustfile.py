import random
import time
from locust import HttpUser, task, between, events

class MoodMarketUser(HttpUser):
    wait_time = between(1, 3)
    
    # Representative sample of tickers for testing
    TICKERS = ["AAPL", "MSFT", "TSLA", "NVDA", "GME", "AMC", "META", "AMZN", "NFLX", "GOOGL"]
    
    def on_start(self):
        """Called when a Locust user starts before any tasks are scheduled."""
        # Authenticate if needed (mock for now, or use real token if auth enabled)
        self.headers = {"Authorization": "Bearer mock_token_for_load_test"}
        
    @task(10)
    def check_health(self):
        """High frequency: Load balancer health checks"""
        self.client.get("/api/v1/health")
        
    @task(5)
    def check_sentiment(self):
        """Medium frequency: Polling sentiment updates"""
        ticker = random.choice(self.TICKERS)
        self.client.get(f"/api/v1/sentiment/{ticker}", headers=self.headers)
        
    @task(3)
    def check_anomaly(self):
        """Medium-low frequency: Checking for hype storms"""
        ticker = random.choice(self.TICKERS)
        self.client.get(f"/api/v1/anomaly/{ticker}", headers=self.headers)
        
    @task(2)
    def check_forecast(self):
        """Low frequency: Requesting full Informer predictions"""
        ticker = random.choice(self.TICKERS)
        self.client.get(f"/api/v1/price/forecast/{ticker}", headers=self.headers)
        
    @task(1)
    def check_pipeline(self):
        """Very low frequency: Heavy pipeline aggregation"""
        ticker = random.choice(self.TICKERS)
        self.client.get(f"/api/v1/pipeline/{ticker}", headers=self.headers)

@events.test_start.add_listener
def on_test_start(environment, **kwargs):
    print("Starting MoodMarket load test...")
    print("Target: 1000 requests per second")

@events.test_stop.add_listener
def on_test_stop(environment, **kwargs):
    print("MoodMarket load test completed.")
