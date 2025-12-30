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
        confidence: float
    ):
        self.risk_score = risk_score
        self.alert = alert
        self.reason = reason
        self.confidence = confidence


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

        self._client = None
        self._client = None
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

        try:
            # Call BAML agent with timeout
            logger.debug(f"Calling BAML fraud detection for user {event.user_id}")

            # Call the BAML-generated function
            # The actual implementation depends on BAML code generation
            # Note: timeout is configured in BAML client initialization
            result = await self._client.FraudCheck(event)

            # Convert BAML result to our assessment format
            assessment = BAMLFraudAssessment(
                risk_score=float(result.risk_score),
                alert=bool(result.alert),
                reason=str(result.reason),
                confidence=float(result.confidence)
            )

            logger.info(
                f"BAML fraud analysis complete for user {event.user_id}: "
                f"risk_score={assessment.risk_score:.2f}, confidence={assessment.confidence:.2f}"
            )

            return assessment

        except TimeoutError:
            logger.warning(
                f"BAML fraud analysis timed out after {self.timeout_ms}ms "
                f"for user {event.user_id}"
            )
            return None
        except Exception as e:
            logger.error(
                f"Error during BAML fraud analysis for user {event.user_id}: {e}",
                exc_info=True
            )
            return None

    def analyze_fraud_sync(self, event: LoginEvent) -> Optional[BAMLFraudAssessment]:
        """
        Synchronous wrapper for fraud analysis.

        This is a convenience method for synchronous contexts.
        Uses asyncio.run internally.

        Args:
            event: LoginEvent with authentication details and context

        Returns:
            BAMLFraudAssessment if successful, None if BAML unavailable or error occurs
        """
        if not self.is_available():
            return None

        try:
            return asyncio.run(self.analyze_fraud(event))
        except Exception as e:
            logger.error(f"Error in synchronous BAML call: {e}", exc_info=True)
            return None


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
