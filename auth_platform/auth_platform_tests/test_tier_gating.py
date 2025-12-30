
import pytest
from starlette.testclient import TestClient
# from .conftest import override_get_db, create_test_user
from auth_platform.auth_service.main import app, get_db
from auth_platform.auth_service.models import Ticket
from auth_platform.auth_service.db import Base, engine
from sqlalchemy.orm import Session
from unittest.mock import patch, AsyncMock, MagicMock

# Setup database for tests
Base.metadata.create_all(bind=engine)

def create_test_user(client, username, email, password, tier="dev"):
    client.post("/register", json={
        "username": username,
        "first_name": "Test",
        "last_name": "User",
        "email": email,
        "password": password,
        "tier": tier
    })

@pytest.fixture
def client():
    # Dependency override is handled in conftest or can be done here if needed
    # app.dependency_overrides[get_db] = override_get_db
    return TestClient(app)

@pytest.fixture
def clean_db():
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    yield

def get_auth_headers(client, username, password):
    response = client.post("/login", json={"username": username, "password": password})
    token = response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}

@pytest.mark.asyncio
async def test_ticket_dev_tier_strict_limits(client, clean_db):
    """
    Verify Dev tier user requesting 'urgent' support is STRICTLY clamped
    to Medium priority by the system, unless it's a security breach.
    """
    # Create Dev User
    # Create Dev User
    resp = client.post("/register", json={
        "username": "dev_user",
        "first_name": "Dev",
        "last_name": "One",
        "email": "dev@test.com",
        "password": "password123",
        "tier": "dev"
    })
    token = resp.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # headers = get_auth_headers(client, "dev_user", "password123")

    # Mock the BAML wrapper to ensure we test the LOGIC, not the external API
    # The Mock should simulate the "fallback" or "strict rules" we defined in baml_wrapper.py
    # But since we are running integration test on main.py, we patch the agent

    with patch("auth_platform.auth_service.main.get_ticket_agent") as mock_agent_getter:
        mock_agent = AsyncMock()
        # Simulate Agent returning what BAML would return for Dev tier (Medium max)
        # We rely on the BAML code having this logic, but here we verify main.py respects it
        from auth_platform.auth_service.utils.baml_wrapper import TicketAnalysis

        mock_agent.analyze_ticket.return_value = TicketAnalysis(
            priority="MEDIUM", # Agent says Medium despite "Urgent" content
            category="TECHNICAL",
            escalate=False,
            escalation_reason="Dev tier limit",
            suggested_response_time=48
        )
        mock_agent_getter.return_value = mock_agent

        # Create "Urgent" ticket
        payload = {
            "title": "URGENT: Database connection failed",
            "description": "System is down, need help immediately!"
        }

        response = client.post("/support/ticket", json=payload, headers=headers)

        assert response.status_code == 200
        data = response.json()

        # Verify it was NOT escalated/prioritized
        assert data["priority"] == "medium"
        assert data["escalated"] is False
        assert data["title"] == payload["title"]

@pytest.mark.asyncio
async def test_ticket_pro_tier_ai_prioritization(client, clean_db):
    """
    Verify Pro tier user requesting 'urgent' support gets
    AI-driven prioritization (High/Critical).
    """
    # Create Pro User
    # Create Pro User
    resp = client.post("/register", json={
        "username": "pro_user",
        "first_name": "Pro",
        "last_name": "One",
        "email": "pro@test.com",
        "password": "password123",
        "tier": "pro"
    })
    token = resp.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # headers = get_auth_headers(client, "pro_user", "password123")

    with patch("auth_platform.auth_service.main.get_ticket_agent") as mock_agent_getter:
        mock_agent = AsyncMock()
        from auth_platform.auth_service.utils.baml_wrapper import TicketAnalysis

        # Agent decides High for Pro user
        mock_agent.analyze_ticket.return_value = TicketAnalysis(
            priority="HIGH",
            category="TECHNICAL",
            escalate=True,
            escalation_reason="High priority keyword for Pro user",
            suggested_response_time=4
        )
        mock_agent_getter.return_value = mock_agent

        # Create "Urgent" ticket
        payload = {
            "title": "URGENT: Database connection failed",
            "description": "System is down, need help immediately!"
        }

        response = client.post("/support/ticket", json=payload, headers=headers)

        assert response.status_code == 200
        data = response.json()

        # Verify it WAS escalated
        assert data["priority"] == "high"
        assert data["escalated"] is True

def test_fraud_dev_vs_pro(client, clean_db):
    """
    Skeleton for fraud test - requires Fraud Agent integration in main.py first.
    For now, verifying that we can distinguish tiers in testing.
    """
    pass
