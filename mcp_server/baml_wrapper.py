"""
BAML client for interfacing with the fraud detection agent.

This module provides a wrapper around the BAML-generated client
for fraud detection analysis.
"""
import logging
import time
from typing import Optional
from datetime import datetime
import asyncio
logger = logging.getLogger(__name__)


import os
import json

from mcp_server.baml_client.types import LoginEvent

# Try to import BAML generated client at module level
try:
    from mcp_server.baml_client import b as baml
    BAML_AVAILABLE = True
except ImportError:
    BAML_AVAILABLE = False
    baml = None

class TokenBucket:
    """
    Token bucket algorithm for rate limiting.
    """
    def __init__(self, capacity: int, fill_rate: float):
        """
        Initialize token bucket.

        Args:
            capacity: Maximum number of tokens in the bucket
            fill_rate: Number of tokens added per second
        """
        self.capacity = float(capacity)
        self._tokens = float(capacity)
        self.fill_rate = fill_rate
        self.last_update = time.time()

    def consume(self, tokens: int = 1) -> bool:
        """
        Attempt to consume tokens from the bucket.

        Args:
            tokens: Number of tokens to consume

        Returns:
            True if tokens were consumed, False if not enough tokens
        """
        now = time.time()
        time_passed = now - self.last_update
        self._tokens += time_passed * self.fill_rate
        if self._tokens > self.capacity:
            self._tokens = self.capacity
        self.last_update = now

        if self._tokens >= tokens:
            self._tokens -= tokens
            return True
        return False



class BAMLFraudAssessment:
    """
    Output data structure from BAML fraud detection agent.

    Contains the risk assessment results from the AI agent.
    """

    def __init__(
        self,
        risk_score: float,
        alert: bool,
        reason: str,
        confidence: float,
        model: str = "unknown"
    ):
        self.risk_score = risk_score
        self.alert = alert
        self.reason = reason
        self.confidence = confidence
        self.model = model


class BAMLClient:
    """
    Client for interfacing with BAML fraud detection agent.

    Handles communication with the BAML runtime and provides
    error handling and timeout management.
    """

    def __init__(self, timeout_ms: int = 5000, max_requests_per_minute: int = 60):
        """
        Initialize BAML client.

        Args:
            timeout_ms: Timeout for BAML agent calls in milliseconds
            max_requests_per_minute: Maximum number of requests allowed per minute
        """
        self.timeout_ms = timeout_ms
        self.max_requests_per_minute = max_requests_per_minute

        # Initialize token bucket for rate limiting
        # Capacity = max_requests_per_minute
        # Fill rate = max_requests_per_minute / 60.0 (tokens per second)
        self.rate_limiter = TokenBucket(
            capacity=max_requests_per_minute,
            fill_rate=max_requests_per_minute / 60.0
        )

        self._initialized = False

        self._client = baml
        self._initialized = BAML_AVAILABLE

        if self._initialized:
             logger.info("BAML client initialized successfully")
        else:
             logger.warning("BAML client not available: ImportError")
             logger.warning("Fraud detection will fall back to rule-based analysis")

    def is_available(self) -> bool:
        """
        Check if BAML client is available and initialized.

        Returns:
            True if BAML client is ready to use, False otherwise
        """
        return self._initialized and self._client is not None

    async def analyze_fraud(self, event: LoginEvent) -> Optional[BAMLFraudAssessment]:
        """
        Analyze an authentication event for fraud using BAML agent.

        Args:
            event: LoginEvent with authentication details and context

        Returns:
            BAMLFraudAssessment if successful, None if BAML unavailable or error occurs
        """
        if not self.is_available():
            logger.warning("BAML client not available for fraud analysis")
            return None

        # Check rate limit
        if not self.rate_limiter.consume(1):
            logger.warning(
                f"BAML rate limit exceeded ({self.max_requests_per_minute} RPM). "
                "Falling back to rule-based detection."
            )
            return None

        if not self._client:
            logger.error("BAML client not initialized")
            return None

        # Retry Config
        max_retries = 3
        base_delay = 2

        ai_model = os.environ.get("AI_MODEL", "groq").lower()

        log_entry = {
            "timestamp": datetime.now().isoformat(),
            "model": ai_model,
            "user_id": event.user_id,
            "event_type": event.event_type,
            "risk_score": None,
            "confidence": None,
            "alert": False,
            "reason": None,
            "error": None
        }

        try:
            # Call BAML agent with retry logic
            logger.debug(f"Calling BAML fraud detection for user {event.user_id}")

            result = None
            for attempt in range(max_retries):
                try:
                    if ai_model == "gemini":
                        logger.info(f"Using Gemini model for fraud check (AI_MODEL={ai_model}) - Attempt {attempt+1}/{max_retries}")
                        result = await self._client.FraudCheckGemini(event)
                    else:
                        logger.info(f"Using Groq model for fraud check (AI_MODEL={ai_model}) - Attempt {attempt+1}/{max_retries}")
                        result = await self._client.FraudCheck(event)
                    break # Success
                except Exception as e:
                    # Check for 429 in message string since exception type might be generic BamlClientHttpError
                    err_msg = str(e)
                    if "429" in err_msg or "Too Many Requests" in err_msg:
                        if attempt < max_retries - 1:
                            wait_time = base_delay * (2 ** attempt)
                            logger.warning(f"Rate limited. Retrying in {wait_time}s...")
                            await asyncio.sleep(wait_time)
                            continue
                    raise e # Re-raise if not 429 or max retries reached

            # Convert BAML result to our assessment format
            assessment = BAMLFraudAssessment(
                risk_score=float(result.risk_score),
                alert=bool(result.alert),
                reason=str(result.reason),
                confidence=float(result.confidence),
                model=ai_model
            )

            # Update log entry
            log_entry.update({
                "risk_score": assessment.risk_score,
                "confidence": assessment.confidence,
                "alert": assessment.alert,
                "reason": assessment.reason
            })

            self._log_response(ai_model, log_entry)

            logger.info(
                f"BAML fraud analysis complete for user {event.user_id}: "
                f"risk_score={assessment.risk_score:.2f}, confidence={assessment.confidence:.2f}"
            )

            return assessment

        except TimeoutError:
            log_entry["error"] = "TimeoutError"
            self._log_response(ai_model, log_entry)
            logger.warning(
                f"BAML fraud analysis timed out after {self.timeout_ms}ms "
                f"for user {event.user_id}"
            )
            return None
        except Exception as e:
            log_entry["error"] = str(e)
            self._log_response(ai_model, log_entry)
            logger.error(
                f"Error during BAML fraud analysis for user {event.user_id}: {e}",
                exc_info=True
            )
            return None

    def _log_response(self, ai_model: str, log_entry: dict):
        """Helper to log AI response (or error) to file."""
        try:
            project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
            log_dir = os.path.join(project_root, "logs", ai_model, "mcp_server")
            os.makedirs(log_dir, exist_ok=True)
            log_path = os.path.join(log_dir, "results.log")

            with open(log_path, "a") as f:
                f.write(json.dumps(log_entry) + "\n")
        except Exception as e:
            logger.error(f"Failed to write to log file: {e}")



# Global BAML client instance
_baml_client: Optional[BAMLClient] = None


def get_baml_client(timeout_ms: int = 5000) -> BAMLClient:
    """
    Get or create the global BAML client instance.

    Args:
        timeout_ms: Timeout for BAML agent calls in milliseconds

    Returns:
        BAMLClient instance
    """
    global _baml_client
    if _baml_client is None:
        _baml_client = BAMLClient(timeout_ms=timeout_ms)
    return _baml_client
