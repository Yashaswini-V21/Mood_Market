import asyncio
import logging
import yaml
import os
from datetime import datetime
from typing import Dict, Any, List, Optional

from agents.sentiment_agent import SentimentAgent
from agents.technical_agent import TechnicalAgent
from agents.forecaster_agent import ForecasterAgent
from agents.risk_manager_agent import RiskManagerAgent
from agents.synthesizer_agent import SynthesizerAgent

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("orchestrator")

class AgentOrchestrator:
    """
    Orchestrator for Multi-Agent Trading System.
    Manages sequential execution flow: S1 -> S2 -> S3 -> S4 -> S5.
    Uses async queues, enforces per-agent timeouts, provides error recovery,
    and returns standardized JSON output payloads.
    """
    
    def __init__(self, config_path: str = "agent_config.yaml"):
        self.config_path = config_path
        self.config = self._load_config()
        self.logger = logger
        
        # Load global settings
        global_cfg = self.config.get("global", {})
        self.cache_ttl = global_cfg.get("cache_ttl_seconds", 300)
        self.timeout = global_cfg.get("timeout_seconds", 30)
        
        # Initialize agents
        self.agents = {
            "sentiment_analyst": SentimentAgent(self.config.get("sentiment_agent", {}), self.cache_ttl),
            "technical_analyst": TechnicalAgent(self.config.get("technical_agent", {}), self.cache_ttl),
            "forecaster": ForecasterAgent(self.config.get("forecaster_agent", {}), self.cache_ttl),
            "risk_manager": RiskManagerAgent(self.config.get("risk_manager_agent", {}), self.cache_ttl),
            "synthesizer": SynthesizerAgent(self.config.get("synthesizer_agent", {}), self.cache_ttl),
        }
        
        self.agent_tasks: List[asyncio.Task] = []
        self._running = False
        
    def _load_config(self) -> Dict[str, Any]:
        """Loads configuration from YAML file."""
        if not os.path.exists(self.config_path):
            self.logger.warning(f"Configuration file {self.config_path} not found. Using empty defaults.")
            return {}
        try:
            with open(self.config_path, "r") as f:
                return yaml.safe_load(f) or {}
        except Exception as e:
            self.logger.error(f"Failed to parse config file: {e}. Using empty defaults.")
            return {}
            
    async def start(self):
        """Starts run loops for all agents as background tasks."""
        if self._running:
            return
        self._running = True
        self.logger.info("Starting background execution loops for all agents.")
        
        # We start all agents in the pipeline
        for name, agent in self.agents.items():
            task = asyncio.create_task(agent.run())
            self.agent_tasks.append(task)
            
    async def stop(self):
        """Stops all agent loops gracefully using cancellation."""
        if not self._running:
            return
        self._running = False
        self.logger.info("Stopping agent background execution loops...")
        
        # Cancel all tasks to stop stuck/slow operations
        if self.agent_tasks:
            for task in self.agent_tasks:
                task.cancel()
            await asyncio.gather(*self.agent_tasks, return_exceptions=True)
            self.agent_tasks.clear()
        self.logger.info("All agent background execution loops stopped.")

    async def execute_pipeline(self, input_payload: Dict[str, Any]) -> Dict[str, Any]:
        """
        Executes the sequential multi-agent execution pipeline.
        S1 (Sentiment) -> S2 (Technical) -> S3 (Forecaster) -> S4 (Risk Manager) -> S5 (Synthesizer)
        Enforces 30-sec timeouts and recovers from failures with fallback behaviors.
        """
        # Ensure agent loops are running
        await self.start()
        
        ticker = input_payload.get("ticker", self.config.get("global", {}).get("default_ticker", "AAPL"))
        timestamp = input_payload.get("timestamp", datetime.utcnow().isoformat() + "Z")
        
        # Build initial accumulator state
        state = input_payload.copy()
        state["ticker"] = ticker
        state["timestamp"] = timestamp
        if "agents" not in state:
            state["agents"] = {}
            
        # Flow definition: list of tuples (agent_key, agent_instance)
        pipeline_flow = [
            ("sentiment_analyst", self.agents["sentiment_analyst"]),
            ("technical_analyst", self.agents["technical_analyst"]),
            ("forecaster", self.agents["forecaster"]),
            ("risk_manager", self.agents["risk_manager"]),
            ("synthesizer", self.agents["synthesizer"])
        ]
        
        for name, agent in pipeline_flow:
            self.logger.info(f"Orchestrating {name} for ticker: {ticker}...")
            
            # Put payload into agent's input queue
            await agent.incoming_queue.put(state)
            
            try:
                # Retrieve from agent's output queue with timeout enforcement
                state = await asyncio.wait_for(
                    agent.outgoing_queue.get(), 
                    timeout=float(self.timeout)
                )
                
                # Check for sentinel or bad output
                if state is None:
                    raise RuntimeError(f"Agent {name} output queue returned None sentinel.")
                    
            except asyncio.TimeoutError:
                self.logger.error(f"Agent {name} execution timed out (limit: {self.timeout}s).")
                # Fallback recovery
                fallback = agent.get_fallback_output(state, asyncio.TimeoutError("Timeout limit exceeded"))
                state["agents"][name] = fallback
                # Clear queue blockages by purging tasks if necessary
                # Reset the agent's queue logic safely
                while not agent.outgoing_queue.empty():
                    agent.outgoing_queue.get_nowait()
            except Exception as e:
                self.logger.error(f"Agent {name} pipeline execution failed: {e}")
                # Fallback recovery
                fallback = agent.get_fallback_output(state, e)
                state["agents"][name] = fallback
                
            # Log audit trail for the agent's output decision
            self.logger.info(f"Audit Trail - Agent {name} output: {state['agents'].get(name)}")
            
        # Standardize final output structure exactly to requested JSON format
        final_payload = {
            "ticker": ticker,
            "timestamp": timestamp,
            "agents": {
                "sentiment_analyst": state["agents"].get("sentiment_analyst"),
                "technical_analyst": state["agents"].get("technical_analyst"),
                "forecaster": state["agents"].get("forecaster"),
                "risk_manager": state["agents"].get("risk_manager")
            },
            "synthesizer": state["agents"].get("synthesizer")
        }
        
        return final_payload
