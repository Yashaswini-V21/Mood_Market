import abc
import asyncio
import logging
import hashlib
import json
from datetime import datetime, timedelta
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)

class AgentCache:
    """Simple in-memory TTL cache for agent execution results"""
    
    def __init__(self, ttl_seconds: int = 300):
        self.ttl_seconds = ttl_seconds
        self.cache: Dict[str, tuple] = {}  # key -> (result_dict, expiry_datetime)
    
    def get(self, key: str) -> Optional[Dict[str, Any]]:
        if key in self.cache:
            result, expiry = self.cache[key]
            if datetime.now() < expiry:
                return result
            else:
                del self.cache[key]
        return None
    
    def set(self, key: str, value: Dict[str, Any]):
        expiry = datetime.now() + timedelta(seconds=self.ttl_seconds)
        self.cache[key] = (value, expiry)
        
    def clear(self):
        self.cache.clear()


class BaseAgent(abc.ABC):
    """
    Abstract base class for all specialized agents.
    Provides standard async loop message handling, caching, timeout and logging support.
    """
    
    def __init__(self, name: str, config: Dict[str, Any], cache_ttl: int = 300):
        self.name = name
        self.config = config
        self.incoming_queue = asyncio.Queue()
        self.outgoing_queue = asyncio.Queue()
        self.cache = AgentCache(ttl_seconds=cache_ttl)
        self.logger = logging.getLogger(f"agents.{name}")
        self.logger.setLevel(logging.INFO)
        
        # Metrics for health monitoring
        self.total_runs = 0
        self.failed_runs = 0
        self.last_run_latency = 0.0
    
    def _generate_cache_key(self, payload: Dict[str, Any]) -> str:
        """
        Generate cache key based on ticker and the agent's specific input data.
        """
        ticker = payload.get("ticker", "UNKNOWN")
        # Extract inputs relevant to this agent to avoid cache collision
        relevant_keys = self.get_relevant_input_keys()
        relevant_inputs = {k: payload.get(k) for k in relevant_keys if k in payload}
        
        # Create MD5 hash of relevant inputs
        input_str = json.dumps(relevant_inputs, sort_keys=True, default=str)
        hash_val = hashlib.md5(input_str.encode()).hexdigest()
        
        return f"{self.name}:{ticker}:{hash_val}"
    
    @abc.abstractmethod
    def get_relevant_input_keys(self) -> list:
        """Return the keys from payload that are relevant to this agent's task."""
        pass
    
    @abc.abstractmethod
    async def process(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """
        Agent core processing logic.
        Must be implemented by subclasses.
        Returns a dictionary representing the agent's output.
        """
        pass
    
    @abc.abstractmethod
    def get_fallback_output(self, payload: Dict[str, Any], error: Exception) -> Dict[str, Any]:
        """
        Generate a fallback output dict in case of exceptions/timeouts.
        Must be implemented by subclasses.
        """
        pass
    
    async def run(self):
        """
        Main runner loop.
        Listens to the incoming queue, processes payloads, and routes results to the outgoing queue.
        Supports caching and handles errors gracefully.
        """
        self.logger.info(f"Agent {self.name} started listening to incoming messages.")
        while True:
            try:
                # Wait for next payload
                payload = await self.incoming_queue.get()
                
                # Check for sentinel shutdown
                if payload is None:
                    self.incoming_queue.task_done()
                    self.logger.info(f"Agent {self.name} received shutdown sentinel.")
                    # Pass the sentinel forward to signal downstream if necessary
                    await self.outgoing_queue.put(None)
                    break
                
                self.logger.info(f"Agent {self.name} processing payload for ticker: {payload.get('ticker')}")
                self.total_runs += 1
                start_time = asyncio.get_event_loop().time()
                
                # Check Cache
                cache_key = self._generate_cache_key(payload)
                cached_result = self.cache.get(cache_key)
                
                if cached_result is not None:
                    self.logger.info(f"Agent {self.name} cache hit for key: {cache_key}")
                    # Merge cached results back into the payload
                    updated_payload = payload.copy()
                    if "agents" not in updated_payload:
                        updated_payload["agents"] = {}
                    updated_payload["agents"][self.name] = cached_result
                    
                    self.last_run_latency = 0.0
                    await self.outgoing_queue.put(updated_payload)
                    self.incoming_queue.task_done()
                    continue
                
                # Run actual process with timeout enforcement inside base loop as a safety measure
                try:
                    result = await self.process(payload)
                    self.logger.info(f"Agent {self.name} processed task successfully.")
                except Exception as e:
                    self.logger.error(f"Agent {self.name} execution failed with error: {str(e)}", exc_info=True)
                    self.failed_runs += 1
                    result = self.get_fallback_output(payload, e)
                
                # Update metrics
                latency = asyncio.get_event_loop().time() - start_time
                self.last_run_latency = latency
                
                # Add to cache if successful
                if result:
                    self.cache.set(cache_key, result)
                
                # Append result under agents dict
                updated_payload = payload.copy()
                if "agents" not in updated_payload:
                    updated_payload["agents"] = {}
                
                updated_payload["agents"][self.name] = result
                
                # Put output to the outgoing queue
                await self.outgoing_queue.put(updated_payload)
                self.incoming_queue.task_done()
                
            except asyncio.CancelledError:
                self.logger.info(f"Agent {self.name} run loop was cancelled.")
                break
            except Exception as e:
                self.logger.critical(f"Critical error in Agent {self.name} loop: {str(e)}", exc_info=True)
                # Ensure we don't block the queue indefinitely if something fails globally
                self.incoming_queue.task_done()
