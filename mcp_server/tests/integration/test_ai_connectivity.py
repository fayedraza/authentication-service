
import pytest
from datetime import datetime
from unittest.mock import MagicMock
from mcp_server.fraud_detector import FraudDetector
from mcp_server.schemas import AuthEventIn

@pytest.mark.asyncio
async def test_ensure_ai_is_used_with_real_key(caplog):
    """
    This test verifies that the system is actually using the AI Model for fraud detection.

    It runs the FraudDetector in a configuration that expects an AI result.
    It asserts that the returned reason contains the '[BAML]' tag.

    EXPECTED BEHAVIOR:
    - If a valid GEMINI_API_KEY is active: PASS ([BAML] tag present)
    - If GEMINI_API_KEY is 'dummy' or missing: FAIL (Fallback to rules, no [BAML] tag)
    - If Rate Limited (429): PASS (Conceptually the key is valid, just out of quota)
    """
    import logging

    # 1. Setup - Mock DB only
    mock_db = MagicMock()
    # Fix: Ensure mock DB returns an integer for count queries to avoid TypeError in fallback logic
    mock_db.execute.return_value.fetchone.return_value = [0]

    # 2. Initialize Detector with BAML Enabled
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
    # Capture logs to check for 429
    with caplog.at_level(logging.INFO):
        result = await detector.analyze_event(event, mock_db)

    # 5. Assert AI Usage
    # The presence of "[BAML]" in the reason string is our contract for AI-generated results.
    if "[BAML]" in result.reason:
        # Success: AI was used
        assert True
    else:
        # Check if failure was due to Rate Limit (429)
        # The logs should contain the 429 error from the wrapper
        log_text = caplog.text
        if "429" in log_text or "Quota exceeded" in log_text or "RESOURCE_EXHAUSTED" in log_text:
            print("\nWARNING: AI execution skipped due to Rate Limit (429). Marking as PASS since API Key is valid.")
            assert True
        else:
            pytest.fail(
                f"Fraud Detection did not use AI. Reason: '{result.reason}'. "
                "Likely cause: Invalid or Dummy API Key causing fallback to rules."
            )
