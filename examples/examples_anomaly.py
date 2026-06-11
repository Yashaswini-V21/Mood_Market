"""
Comprehensive examples for Hype Storm anomaly detection system.
Demonstrates real-world usage patterns and best practices.
"""

import os
import sys
import numpy as np

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
import json
from datetime import datetime, timedelta
from anomaly_detector import AnomalyDetector
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# ============================================================================
# Example 1: Basic Setup and Single Stock Monitoring
# ============================================================================

def example_basic_setup():
    """Basic setup for monitoring a single stock"""
    logger.info("=== Example 1: Basic Setup ===\n")
    
    # Initialize detector
    detector = AnomalyDetector(
        zscore_threshold=3.0,
        ensemble_threshold=0.65,
        confidence_threshold=0.7
    )
    
    # Generate 30-day baseline (2880 samples = 30 days × 96 15-min windows)
    np.random.seed(42)
    reddit_history = np.random.normal(100, 10, 2880)
    google_history = np.random.normal(50, 5, 2880)
    twitter_history = np.random.normal(200, 20, 2880)
    
    # Fit baseline for Apple
    detector.fit_baseline(
        "AAPL",
        reddit_history,
        google_history,
        twitter_history
    )
    
    logger.info("✓ Baseline fitted for AAPL\n")
    
    # Test normal conditions
    logger.info("Test 1: Normal conditions")
    alert = detector.predict("AAPL", reddit_volume=100, google_trends_score=50, twitter_volume=200)
    logger.info(f"  Anomaly: {alert.anomaly_detected}")
    logger.info(f"  Confidence: {alert.confidence:.1%}\n")
    
    # Test spike conditions
    logger.info("Test 2: Mild spike")
    alert = detector.predict("AAPL", reddit_volume=200, google_trends_score=65, twitter_volume=300)
    logger.info(f"  Anomaly: {alert.anomaly_detected}")
    logger.info(f"  Confidence: {alert.confidence:.1%}\n")
    
    # Test extreme spike
    logger.info("Test 3: Extreme spike (Hype Storm)")
    alert = detector.predict("AAPL", reddit_volume=500, google_trends_score=90, twitter_volume=800)
    logger.info(f"  Anomaly: {alert.anomaly_detected}")
    logger.info(f"  Alert Type: {alert.alert_type}")
    logger.info(f"  Confidence: {alert.confidence:.1%}")
    logger.info(f"  Recommendation: {alert.recommendation}")
    logger.info(f"  Methods Triggered: {alert.methods_triggered}\n")


# ============================================================================
# Example 2: Multi-Stock Portfolio Monitoring
# ============================================================================

def example_portfolio_monitoring():
    """Monitor a portfolio of multiple stocks"""
    logger.info("=== Example 2: Portfolio Monitoring ===\n")
    
    detector = AnomalyDetector(n_stocks=500)
    
    # Portfolio of 10 stocks
    portfolio = {
        "AAPL": {"reddit_baseline": 100, "google_baseline": 50, "twitter_baseline": 200},
        "MSFT": {"reddit_baseline": 80, "google_baseline": 45, "twitter_baseline": 150},
        "TSLA": {"reddit_baseline": 150, "google_baseline": 60, "twitter_baseline": 300},
        "GME": {"reddit_baseline": 200, "google_baseline": 70, "twitter_baseline": 400},
        "DOGE": {"reddit_baseline": 250, "google_baseline": 75, "twitter_baseline": 500},
    }
    
    # Fit baseline for each stock
    np.random.seed(42)
    baseline_data = np.random.normal(100, 10, 2880)
    
    for ticker, config in portfolio.items():
        reddit_data = baseline_data * (config["reddit_baseline"] / 100)
        google_data = baseline_data * (config["google_baseline"] / 100)
        twitter_data = baseline_data * (config["twitter_baseline"] / 100)
        
        detector.fit_baseline(ticker, reddit_data, google_data, twitter_data)
        logger.info(f"✓ Fitted baseline for {ticker}")
    
    logger.info()
    
    # Generate random alerts
    alerts_generated = []
    for ticker, config in portfolio.items():
        # Random multiplier for volume
        reddit_mult = np.random.uniform(0.8, 5.0)
        google_mult = np.random.uniform(0.8, 5.0)
        twitter_mult = np.random.uniform(0.8, 5.0)
        
        alert = detector.predict(
            ticker,
            reddit_volume=config["reddit_baseline"] * reddit_mult,
            google_trends_score=config["google_baseline"] * google_mult,
            twitter_volume=config["twitter_baseline"] * twitter_mult
        )
        
        if alert.anomaly_detected:
            alerts_generated.append(alert)
    
    # Report anomalies
    logger.info(f"Alerts generated: {len(alerts_generated)}\n")
    for alert in alerts_generated:
        logger.info(f"{alert.ticker}: {alert.alert_type}")
        logger.info(f"  Confidence: {alert.confidence:.1%}")
        logger.info(f"  Recommendation: {alert.recommendation}\n")


# ============================================================================
# Example 3: Real-Time Streaming Monitoring
# ============================================================================

def example_realtime_streaming():
    """Simulate real-time streaming data monitoring"""
    logger.info("=== Example 3: Real-Time Streaming ===\n")
    
    detector = AnomalyDetector()
    
    # Fit initial baseline
    np.random.seed(42)
    baseline = np.random.normal(100, 10, 2880)
    detector.fit_baseline("STREAM", baseline, baseline/2, baseline*2)
    
    logger.info("Baseline fitted. Starting stream monitoring...\n")
    
    # Simulate 24-hour streaming (96 15-min windows)
    # First 12 hours normal, last 12 hours with spike
    alerts_detected = []
    
    for hour in range(24):
        for window in range(4):  # 4 windows per hour
            
            if hour < 12:
                # Normal conditions
                reddit = np.random.normal(100, 10)
                google = np.random.normal(50, 5)
                twitter = np.random.normal(200, 20)
            else:
                # Gradual spike in afternoon
                spike_factor = 1 + (hour - 12) * 0.2  # Increases over time
                reddit = np.random.normal(100 * spike_factor, 10)
                google = np.random.normal(50 * spike_factor, 5)
                twitter = np.random.normal(200 * spike_factor, 20)
            
            alert = detector.predict("STREAM", reddit, google, twitter)
            
            if alert.anomaly_detected:
                alerts_detected.append({
                    "time": f"Hour {hour}:{window*15}min",
                    "alert_type": alert.alert_type,
                    "confidence": alert.confidence
                })
    
    logger.info(f"Detected {len(alerts_detected)} anomalies over 24 hours:\n")
    for alert in alerts_detected[-5:]:  # Show last 5
        logger.info(f"  {alert['time']}: {alert['alert_type']} (conf: {alert['confidence']:.1%})")


# ============================================================================
# Example 4: Historical Events - GME 2021 Squeeze
# ============================================================================

def example_gme_2021_squeeze():
    """Simulate GME 2021 squeeze detection"""
    logger.info("=== Example 4: GME 2021 Squeeze ===\n")
    
    detector = AnomalyDetector(
        zscore_threshold=3.0,
        ensemble_threshold=0.65
    )
    
    # Baseline: Typical GME activity Jan 1-20, 2021
    np.random.seed(42)
    baseline_reddit = np.random.normal(50, 5, 2880)    # ~50 mentions/15min
    baseline_google = np.random.normal(35, 3, 2880)    # ~35 search score
    baseline_twitter = np.random.normal(100, 10, 2880) # ~100 tweets/min
    
    detector.fit_baseline("GME", baseline_reddit, baseline_google, baseline_twitter)
    
    logger.info("GME Baseline (Jan 1-20):")
    baseline = detector.baselines["GME"]
    logger.info(f"  Reddit: {baseline.reddit_mean:.1f} ± {baseline.reddit_std:.1f} mentions/15min")
    logger.info(f"  Google: {baseline.google_trends_mean:.1f} ± {baseline.google_trends_std:.1f} search score")
    logger.info(f"  Twitter: {baseline.twitter_mean:.1f} ± {baseline.twitter_std:.1f} tweets/min\n")
    
    # Simulate squeeze events
    events = [
        {
            "name": "Jan 28 - Initial Squeeze",
            "reddit": 1200,  # ~24x baseline
            "google": 95,
            "twitter": 4500
        },
        {
            "name": "Jan 29 - Peak Frenzy",
            "reddit": 2500,  # ~50x baseline
            "google": 98,
            "twitter": 8000
        },
        {
            "name": "Feb 1 - Cooling Off",
            "reddit": 800,   # ~16x baseline
            "google": 75,
            "twitter": 3000
        }
    ]
    
    for event in events:
        alert = detector.predict(
            "GME",
            reddit_volume=event["reddit"],
            google_trends_score=event["google"],
            twitter_volume=event["twitter"]
        )
        
        logger.info(f"{event['name']}:")
        logger.info(f"  Reddit mentions: {event['reddit']} (~{event['reddit']/baseline.reddit_mean:.1f}x baseline)")
        logger.info(f"  Alert Type: {alert.alert_type}")
        logger.info(f"  Confidence: {alert.confidence:.1%}")
        logger.info(f"  Methods Triggered: {len(alert.methods_triggered)}/7")
        logger.info(f"  Recommendation: {alert.recommendation}\n")


# ============================================================================
# Example 5: Detector Performance Analysis
# ============================================================================

def example_detector_analysis():
    """Analyze individual detector contributions"""
    logger.info("=== Example 5: Detector Performance Analysis ===\n")
    
    detector = AnomalyDetector()
    
    np.random.seed(42)
    baseline = np.random.normal(100, 10, 2880)
    detector.fit_baseline("PERF_TEST", baseline, baseline/2, baseline*2)
    
    # Get detector statistics
    stats = detector.get_detector_stats("PERF_TEST")
    
    logger.info("Individual Detector Statistics:\n")
    for detector_name, detector_stats in stats["detectors"].items():
        logger.info(f"{detector_name}:")
        for key, value in detector_stats.items():
            if key not in ["detector"]:
                logger.info(f"  {key}: {value}")
        logger.info()


# ============================================================================
# Example 6: False Positive Tracking
# ============================================================================

def example_false_positive_tracking():
    """Track and manage false positives"""
    logger.info("=== Example 6: False Positive Tracking ===\n")
    
    detector = AnomalyDetector(confidence_threshold=0.65)  # Lower threshold
    
    np.random.seed(42)
    baseline = np.random.normal(100, 10, 2880)
    detector.fit_baseline("FP_TEST", baseline, baseline/2, baseline*2)
    
    logger.info("Generating predictions and tracking FP...\n")
    
    # Generate 100 predictions, some false positives
    for i in range(100):
        alert = detector.predict(
            "FP_TEST",
            reddit_volume=np.random.normal(100, 10),
            google_trends_score=50,
            twitter_volume=200
        )
        
        # Mark some alerts as false positive
        if alert.anomaly_detected and np.random.random() < 0.7:  # 70% are actually false
            detector.mark_false_positive("FP_TEST")
    
    # Get summary
    summary = detector.get_alert_summary("FP_TEST")
    logger.info(f"Alert Summary for FP_TEST:")
    logger.info(f"  Total alerts: {summary['total_alerts']}")
    logger.info(f"  False positives marked: {summary['false_positives']}")
    logger.info(f"  False positive rate: {summary['false_positive_rate']:.1%}\n")


# ============================================================================
# Example 7: Sensitivity Tuning
# ============================================================================

def example_sensitivity_tuning():
    """Demonstrate sensitivity tuning"""
    logger.info("=== Example 7: Sensitivity Tuning ===\n")
    
    # Create detectors with different sensitivities
    configs = [
        {"name": "Very Conservative", "zscore": 4.0, "ensemble": 0.85},
        {"name": "Conservative", "zscore": 3.5, "ensemble": 0.75},
        {"name": "Balanced", "zscore": 3.0, "ensemble": 0.65},
        {"name": "Aggressive", "zscore": 2.5, "ensemble": 0.55},
        {"name": "Very Aggressive", "zscore": 2.0, "ensemble": 0.45},
    ]
    
    np.random.seed(42)
    baseline = np.random.normal(100, 10, 2880)
    
    # Test spike level
    test_reddit = 350  # 3.5x baseline
    test_google = 80
    test_twitter = 600
    
    logger.info(f"Testing with spike level: Reddit={test_reddit} (3.5x baseline)\n")
    
    for config in configs:
        det = AnomalyDetector(
            zscore_threshold=config["zscore"],
            ensemble_threshold=config["ensemble"]
        )
        det.fit_baseline("TUNE_TEST", baseline, baseline/2, baseline*2)
        
        alert = det.predict("TUNE_TEST", test_reddit, test_google, test_twitter)
        
        logger.info(f"{config['name']}:")
        logger.info(f"  Thresholds: Z-score={config['zscore']}, Ensemble={config['ensemble']:.0%}")
        logger.info(f"  Anomaly Detected: {'✓ YES' if alert.anomaly_detected else '✗ NO'}")
        logger.info(f"  Confidence: {alert.confidence:.1%}\n")


# ============================================================================
# Example 8: Integration with Trading System
# ============================================================================

def example_trading_integration():
    """Example integration with a trading system"""
    logger.info("=== Example 8: Trading System Integration ===\n")
    
    detector = AnomalyDetector()
    
    np.random.seed(42)
    baseline = np.random.normal(100, 10, 2880)
    detector.fit_baseline("TRADING", baseline, baseline/2, baseline*2)
    
    # Simulate trading decisions based on alerts
    portfolio_positions = {
        "TRADING": {"shares": 1000, "entry_price": 150}
    }
    
    # Current market conditions
    current_price = 165
    position_value = portfolio_positions["TRADING"]["shares"] * current_price
    
    # Check for anomalies
    alert = detector.predict("TRADING", reddit_volume=400, google_trends_score=85, twitter_volume=750)
    
    logger.info(f"Current Position:")
    logger.info(f"  Shares: {portfolio_positions['TRADING']['shares']}")
    logger.info(f"  Entry Price: ${portfolio_positions['TRADING']['entry_price']}")
    logger.info(f"  Current Price: ${current_price}")
    logger.info(f"  Position Value: ${position_value:,.0f}\n")
    
    logger.info(f"Market Alert: {alert.alert_type}")
    logger.info(f"Confidence: {alert.confidence:.1%}")
    logger.info(f"Recommendation: {alert.recommendation}\n")
    
    # Trading decision logic
    if alert.recommendation == "REDUCE_POSITION_SIZE":
        reduce_to = int(portfolio_positions["TRADING"]["shares"] * 0.5)
        sell_shares = portfolio_positions["TRADING"]["shares"] - reduce_to
        sell_value = sell_shares * current_price
        logger.info(f"TRADING ACTION:")
        logger.info(f"  Action: REDUCE position by {sell_shares:,} shares")
        logger.info(f"  Sell Value: ${sell_value:,.0f}")
        logger.info(f"  Remaining Position: {reduce_to:,} shares (${reduce_to * current_price:,.0f})\n")
    
    elif alert.recommendation == "INVESTIGATE":
        logger.info(f"TRADING ACTION:")
        logger.info(f"  Action: INVESTIGATE further")
        logger.info(f"  Check: News, earnings, SEC filings\n")
    
    else:
        logger.info(f"TRADING ACTION: No action needed\n")


# ============================================================================
# Main runner
# ============================================================================

def run_all_examples():
    """Run all examples"""
    examples = [
        ("Basic Setup", example_basic_setup),
        ("Portfolio Monitoring", example_portfolio_monitoring),
        ("Real-Time Streaming", example_realtime_streaming),
        ("GME 2021 Squeeze", example_gme_2021_squeeze),
        ("Detector Analysis", example_detector_analysis),
        ("False Positive Tracking", example_false_positive_tracking),
        ("Sensitivity Tuning", example_sensitivity_tuning),
        ("Trading Integration", example_trading_integration),
    ]
    
    for name, example_func in examples:
        try:
            example_func()
            print("\n" + "="*80 + "\n")
        except Exception as e:
            logger.error(f"Error in {name}: {e}\n")


if __name__ == "__main__":
    run_all_examples()
