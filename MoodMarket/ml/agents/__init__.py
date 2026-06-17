"""
Multi-Agent Trading Desk — Agent Package.

Provides five async AI agents that compose a sequential trading intelligence
pipeline: Sentiment → Technical → Forecaster → Risk Manager → Synthesizer.

Each agent inherits from ``BaseAgent`` and communicates via
``asyncio.Queue`` pairs (incoming / outgoing).
"""

from agents.base_agent import BaseAgent
from agents.sentiment_agent import SentimentAgent
from agents.technical_agent import TechnicalAgent
from agents.forecaster_agent import ForecasterAgent
from agents.risk_manager_agent import RiskManagerAgent
from agents.synthesizer_agent import SynthesizerAgent

__all__ = [
    "BaseAgent",
    "SentimentAgent",
    "TechnicalAgent",
    "ForecasterAgent",
    "RiskManagerAgent",
    "SynthesizerAgent",
]
