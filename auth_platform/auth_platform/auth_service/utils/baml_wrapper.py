
import json
import logging
import os
from typing import Optional, List, Dict, Any

logger = logging.getLogger(__name__)

def get_log_path(model: str, functionality: str) -> str:
    # Go up 3 levels from auth_service/utils/baml_wrapper.py to auth_platform root
    # Then up one more to project root where logs/ is mounted
    # Current file: auth_platform/auth_platform/auth_service/utils/baml_wrapper.py
    # .../utils -> .../auth_service -> .../auth_platform -> .../auth_platform(root) -> project_root

    # Actually, simpler to just assume we are in Docker working dir /app
    # But usually creating a logs dir relative to the project root is safer if mounted.
    # In Docker, WORKDIR is /app. We can log to /app/logs if mounted there.
    # Or navigate relative to __file__.

    # Let's use relative path from this file to ensure we hit the mounted volume.
    # This file is in .../auth_platform/auth_service/utils/
    # We want to write to .../logs (if mounted at root of auth_platform).
    # Wait, the plan says "Mount the logs/ directory to both mcp_server and auth_platform".
    # In docker-compose, for auth_platform, generated code is in /app (WORKDIR).
    # We should mount logs to /app/logs.

    base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(os.path.dirname(__file__)))))
    # This might be brittle. Let's just use "logs" in current working directory which is /app.

    log_dir = os.path.join(os.getcwd(), "logs", model, functionality)
    os.makedirs(log_dir, exist_ok=True)
    return os.path.join(log_dir, "results.log")

# Try to import baml_client at module level
try:
    from baml_client import b as baml
    BAML_AVAILABLE = True
except ImportError:
    BAML_AVAILABLE = False
    baml = None

# Output DTOs matching BAML definition
class TicketAnalysis:
    def __init__(
        self,
        priority: str,
        category: str,
        escalate: bool,
        escalation_reason: Optional[str] = None,
        suggested_response_time: int = 24,
        tags: List[str] = None,
        urgency_score: float = 0.0,
        customer_impact_level: str = "MINIMAL",
        recommended_assignee: str = "TIER1_SUPPORT"
    ):
        self.priority = priority.upper()
        self.category = category.upper()
        self.escalate = escalate
        self.escalation_reason = escalation_reason
        self.suggested_response_time = suggested_response_time
        self.tags = tags or []
        self.urgency_score = urgency_score
        self.customer_impact_level = customer_impact_level
        self.recommended_assignee = recommended_assignee

class OwnerContext:
    def __init__(
        self,
        previous_ticket_count: int,
        account_age_days: int,
        last_ticket_date: Optional[str],
        avg_resolution_time_hours: float,
        tier_upgrade_date: Optional[str] = None,
        total_api_calls_last_month: int = 0
    ):
        self.previous_ticket_count = previous_ticket_count
        self.account_age_days = account_age_days
        self.last_ticket_date = last_ticket_date
        self.avg_resolution_time_hours = avg_resolution_time_hours
        self.tier_upgrade_date = tier_upgrade_date
        self.total_api_calls_last_month = total_api_calls_last_month

class AuthEvent:
    def __init__(self, event_type: str, ip_address: str, user_agent: str, timestamp: str, success: bool = True):
        self.event_type = event_type
        self.ip_address = ip_address
        self.user_agent = user_agent
        self.timestamp = timestamp
        self.success = success

class FraudAssessment:
    def __init__(
        self,
        risk_level: str,
        risk_score: float,
        action: str,
        reason: str,
        confidence: float,
        risk_factors: List[str]
    ):
        self.risk_level = risk_level
        self.risk_score = risk_score
        self.action = action
        self.reason = reason
        self.confidence = confidence
        self.risk_factors = risk_factors

class BamlTicketAgent:
    _instance = None

    def __init__(self):
        self._client = baml
        self._available = BAML_AVAILABLE
        if self._available:
             logger.info("BAML Ticket Agent initialized successfully.")
        else:
             logger.warning("BAML client not found. Running in MOCK mode.")

    @classmethod
    def get_instance(cls):
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def is_available(self):
        return self._available

    async def analyze_ticket(
        self,
        ticket_id: int,
        title: str,
        description: str,
        owner_tier: str,
        created_at: str,
        owner_context: OwnerContext
    ) -> TicketAnalysis:

        if not self.is_available():
            return self._mock_analysis(title, description, owner_tier)

        try:
            ai_model = os.environ.get("AI_MODEL", "groq").lower()
            logger.info(f"Using {ai_model} model for ticket escalation.")

            # Map input to dictionary as BAML expects
            if ai_model == "gemini":
                result = await self._client.TicketEscalationGemini(
                    ticket_id=ticket_id,
                    title=title,
                    description=description,
                    owner_tier=owner_tier,
                    created_at=created_at,
                    owner_history=owner_context
                )
            else:
                result = await self._client.TicketEscalation(
                    ticket_id=ticket_id,
                    title=title,
                    description=description,
                    owner_tier=owner_tier,
                    created_at=created_at,
                    owner_history=owner_context
                )

            # Map result back to our DTO
            ticket_analysis = TicketAnalysis(
                priority=result.priority,
                category=result.category,
                escalate=result.escalate,
                escalation_reason=result.escalation_reason,
                suggested_response_time=result.suggested_response_time,
                tags=result.tags,
                urgency_score=result.urgency_score,
                customer_impact_level=result.customer_impact_level,
                recommended_assignee=result.recommended_assignee
            )

            # Log result
            try:
                log_path = get_log_path(ai_model, "ticket_escalation")
                log_entry = {
                    "ticket_id": ticket_id,
                    "title": title,
                    "priority": ticket_analysis.priority,
                    "model": ai_model,
                    "timestamp": created_at
                }
                with open(log_path, "a") as f:
                    f.write(json.dumps(log_entry) + "\n")
            except Exception as e:
                logger.error(f"Failed to log ticket analysis: {e}")

            return ticket_analysis

        except Exception as e:
            logger.error(f"Error calling BAML TicketEscalation: {e}")
            # Fallback to mock/safe default on error
            return self._mock_analysis(title, description, owner_tier)

    def _mock_analysis(self, title: str, description: str, owner_tier: str) -> TicketAnalysis:
        """Fallback mock logic if AI is offline"""
        logger.info("Using mock ticket analysis logic (Fallback).")
        content = (title + " " + description).lower()

        priority = "MEDIUM"
        escalate = False
        reason = None

        # Strict mock rules for Dev
        if owner_tier.lower() == "dev":
            if "security" in content or "breach" in content:
                priority = "CRITICAL"
                escalate = True
                reason = "Potential security issue (Dev Tier exception)"
            else:
                priority = "MEDIUM" # Cap at Medium
        else:
            # Pro Tier simple mock logic
            if "urgent" in content or "down" in content:
                priority = "HIGH"
                escalate = True
                reason = "High priority keyword detected for Pro user"

        return TicketAnalysis(
            priority=priority,
            category="GENERAL",
            escalate=escalate,
            escalation_reason=reason,
            suggested_response_time=48 if owner_tier == "dev" else 24
        )

class BamlFraudAgent:
    _instance = None

    def __init__(self):
        self._client = baml
        self._available = BAML_AVAILABLE
        if self._available:
            logger.info("BAML Fraud Agent initialized successfully.")
        else:
            logger.warning("BAML client not found. Running in MOCK mode.")

    @classmethod
    def get_instance(cls):
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def is_available(self):
        return self._available

    async def analyze_risk(
        self,
        user_id: int,
        username: str,
        event_type: str,
        ip_address: str,
        user_agent: str,
        timestamp: str,
        recent_events: List[AuthEvent]
    ) -> FraudAssessment:
        if not self._available:
             return self._mock_analysis(username, ip_address)

        try:
            ai_model = os.environ.get("AI_MODEL", "groq").lower()
            logger.info(f"Using {ai_model} model for fraud detection.")

            if ai_model == "gemini":
                result = await self._client.FraudDetectionGemini(
                    user_id=user_id,
                    username=username,
                    event_type=event_type,
                    ip_address=ip_address,
                    user_agent=user_agent,
                    timestamp=timestamp,
                    recent_events=recent_events
                )
            else:
                result = await self._client.FraudDetection(
                    user_id=user_id,
                    username=username,
                    event_type=event_type,
                    ip_address=ip_address,
                    user_agent=user_agent,
                    timestamp=timestamp,
                    recent_events=recent_events
                )

            fraud_assessment = FraudAssessment(
                risk_level=result.risk_level,
                risk_score=result.risk_score,
                action=result.action,
                reason=result.reason,
                confidence=result.confidence,
                risk_factors=result.risk_factors
            )

            # Log result
            try:
                log_path = get_log_path(ai_model, "fraud_detection")
                log_entry = {
                    "user_id": user_id,
                    "event_type": event_type,
                    "risk_score": fraud_assessment.risk_score,
                    "action": fraud_assessment.action,
                    "model": ai_model,
                    "timestamp": timestamp
                }
                with open(log_path, "a") as f:
                    f.write(json.dumps(log_entry) + "\n")
            except Exception as e:
                logger.error(f"Failed to log fraud assessment: {e}")

            return fraud_assessment

        except Exception as e:
            logger.error(f"Error calling BAML FraudDetection: {e}")
            return self._mock_analysis(username, ip_address)

    def _mock_analysis(self, username: str, ip_address: str) -> FraudAssessment:
        logger.info("Using mock fraud analysis (Fallback).")
        # Simple mock: if IP starts with "10.0.0.", low risk, else medium
        if ip_address.startswith("10.0.0."):
             return FraudAssessment("LOW", 0.1, "ALLOW", "Internal IP - Low Risk", 1.0, [])
        else:
             return FraudAssessment("MEDIUM", 0.4, "ALLOW", "External IP - Monitor", 0.7, ["External IP"])

_fraud_agent = BamlFraudAgent.get_instance()

def get_fraud_agent() -> BamlFraudAgent:
    return BamlFraudAgent.get_instance()

# Global access helper
_agent = BamlTicketAgent.get_instance()

def get_ticket_agent() -> BamlTicketAgent:
    return BamlTicketAgent.get_instance()
