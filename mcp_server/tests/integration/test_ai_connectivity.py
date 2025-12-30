
import pytest
from datetime import datetime
from unittest.mock import MagicMock
from mcp_server.fraud_detector import FraudDetector
from mcp_server.schemas import AuthEventIn

@pytest.mark.asyncio
async def test_ensure_ai_is_used_with_real_key():
    """
    This test verifies that the system is actually using the AI Model for fraud detection.

    It runs the FraudDetector in a configuration that expects an AI result.
    It asserts that the returned reason contains the '[BAML]' tag.

    EXPECTED BEHAVIOR:
    - If a valid BAML_API_KEY is active: PASS ([BAML] tag present)
    - If BAML_API_KEY is 'dummy' or missing: FAIL (Fallback to rules, no [BAML] tag)
    """

    # 1. Setup - Mock DB only (we don't need real DB for this, just the detector logic)
    mock_db = MagicMock()

    # 2. Initialize Detector with BAML Enabled
    # We rely on the global configuration (env vars) for the BAML Client Key
    detector = FraudDetector(baml_enabled=True)

    # 3. Create a sample event
    event = AuthEventIn(
        user_id=999,
        username="integration_test_user",
        event_type="login_success",
        ip_address="1.2.3.4",
        user_agent="TestAgent",
        timestamp=datetime.utcnow().isoformat() + "Z",
        metadata={}
    )

    # 4. Analyze
    result = await detector.analyze_event(event, mock_db)

    # 5. Assert AI Usage
    # The presence of "[BAML]" in the reason string is our contract for AI-generated results.
    # If the system fell back to rules (due to dummy key/errors), this assertion will fail.
    assert "[BAML]" in result.reason, (
        f"Fraud Detection did not use AI. Reason: '{result.reason}'. "
        "Likely cause: Invalid or Dummy API Key causing fallback to rules."
    )
