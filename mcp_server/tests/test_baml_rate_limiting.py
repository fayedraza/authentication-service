import pytest
import time
from unittest.mock import AsyncMock, MagicMock, patch
from mcp_server.baml_wrapper import BAMLClient, TokenBucket

class TestTokenBucket:
    def test_token_consumption(self):
        # 10 tokens per second, capacity 10
        bucket = TokenBucket(capacity=10, fill_rate=10.0)

        # Should be able to consume 10 tokens immediately
        assert bucket.consume(10) is True

        # Should fail to consume more immediately
        assert bucket.consume(1) is False

    def test_token_refill(self):
        # 10 tokens per second
        bucket = TokenBucket(capacity=10, fill_rate=10.0)

        # Consume all tokens
        assert bucket.consume(10) is True

        # Wait 0.1 seconds (should refill 1 token)
        time.sleep(0.11)

        # Should be able to consume 1 token
        assert bucket.consume(1) is True

    def test_capacity_cap(self):
        # 10 tokens per second, capacity 5
        bucket = TokenBucket(capacity=5, fill_rate=10.0)

        # Wait for potential overflow
        time.sleep(0.2)

        # Should only be able to consume capacity (5), not more
        assert bucket.consume(5) is True
        assert bucket.consume(1) is False

@pytest.mark.asyncio
class TestBAMLClientRateLimiting:
    async def test_rate_limit_enforced(self):
        # Create client with very restrictive limit: 60 RPM = 1 RPS
        # For testing, we can manually set the bucket to be empty
        client = BAMLClient(max_requests_per_minute=60)

        # Mock the internal client and is_available
        client._client = MagicMock()
        client._client.FraudCheck = AsyncMock(return_value=MagicMock(risk_score=0.1, alert=False, reason="OK", confidence=1.0))
        client._initialized = True

        # Manually empty the bucket for testing
        client.rate_limiter._tokens = 0

        # Create a dummy event
        mock_event = MagicMock()
        mock_event.user_id = 123

        # Call analyze_fraud - should fail due to rate limit
        result = await client.analyze_fraud(mock_event)

        assert result is None

    async def test_rate_limit_allowed(self):
        client = BAMLClient(max_requests_per_minute=60)

        # Mock the internal client and is_available
        client._client = MagicMock()
        client._client.FraudCheck = AsyncMock(return_value=MagicMock(risk_score=0.1, alert=False, reason="OK", confidence=1.0))
        client._initialized = True

        # Bucket starts full, so this should succeed
        mock_event = MagicMock()
        mock_event.user_id = 123

        result = await client.analyze_fraud(mock_event)

        assert result is not None
        assert result.risk_score == 0.1
