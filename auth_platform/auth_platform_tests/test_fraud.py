
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock
from auth_platform.auth_service.main import app
from auth_platform.auth_service.db import Base, engine, SessionLocal
from auth_platform.auth_service.models import User
from auth_platform.auth_service.auth import hash_password
from auth_platform.auth_service.utils.baml_wrapper import FraudAssessment

client = TestClient(app)

def reset_db():
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)

def ensure_user(username="testuser", password="Secret123!", tier="dev"):
    db = SessionLocal()
    try:
        u = db.query(User).filter(User.username == username).first()
        if not u:
            u = User(username=username, first_name="Test", last_name="User", email=f"{username}@example.com", password=hash_password(password), tier=tier)
            db.add(u)
            db.commit()
        return username
    finally:
        db.close()


from unittest.mock import patch, MagicMock, AsyncMock

# ... imports ...

def test_login_success_low_risk():
    reset_db()
    username = ensure_user()

    # Mock the fraud agent to return LOW risk
    with patch('auth_platform.auth_service.main.get_fraud_agent') as mock_get_agent:
        mock_agent = MagicMock()
        mock_agent.analyze_risk = AsyncMock(return_value=FraudAssessment(
            risk_level="LOW",
            risk_score=0.1,
            action="ALLOW",
            reason="Safe",
            confidence=1.0,
            risk_factors=[]
        ))
        mock_get_agent.return_value = mock_agent

        response = client.post("/login", json={"username": username, "password": "Secret123!"})
        assert response.status_code == 200
        assert "access_token" in response.json()

def test_login_blocked_high_risk():
    reset_db()
    username = ensure_user()

    # Mock the fraud agent to return HIGH risk BLOCK
    with patch('auth_platform.auth_service.main.get_fraud_agent') as mock_get_agent:
        mock_agent = MagicMock()
        mock_agent.analyze_risk = AsyncMock(return_value=FraudAssessment(
            risk_level="HIGH",
            risk_score=0.9,
            action="BLOCK",
            reason="Suspicious Activity",
            confidence=0.9,
            risk_factors=["Bad IP"]
        ))
        mock_get_agent.return_value = mock_agent

        response = client.post("/login", json={"username": username, "password": "Secret123!"})
        # After removing blocking logic, high risk login should still succeed (200)
        # The fraud detection happens asynchronously in the background
        assert response.status_code == 200
        assert "access_token" in response.json()
