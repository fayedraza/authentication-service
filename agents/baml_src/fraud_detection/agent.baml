
// Fraud Detection BAML Agent
// Analyzes authentication events to detect suspicious patterns and assign risk scores

function FraudDetection(
  user_id: int,
  username: string,
  event_type: string,
  ip_address: string,
  user_agent: string,
  timestamp: string,
  recent_events: AuthEvent[]
) -> FraudAssessment {
  client Groq

  prompt #"
    You are a cybersecurity expert analyzing authentication events for fraud detection.

    Analyze the following authentication event for fraud indicators:

    **Current Event:**
    - User ID: {{ user_id }}
    - Username: {{ username }}
    - Event Type: {{ event_type }}
    - IP Address: {{ ip_address }}
    - User Agent: {{ user_agent }}
    - Timestamp: {{ timestamp }}

    **Recent Event History (last 24 hours):**
    {% for event in recent_events %}
    - {{ event.event_type }} from {{ event.ip_address }} at {{ event.timestamp }}
    {% endfor %}

    **Analysis Criteria:**
    1. Geographic anomalies (IP location changes)
    2. Device fingerprint changes (user agent variations)
    3. Temporal patterns (unusual login times, rapid succession)
    4. Failed attempt frequency and patterns
    5. Velocity checks (multiple attempts from different IPs)
    6. Known attack patterns (brute force, credential stuffing)

    **Risk Assessment Guidelines:**
    - LOW (0.0-0.3): Normal behavior, no suspicious indicators
    - MEDIUM (0.3-0.7): Some anomalies detected, monitor closely
    - HIGH (0.7-1.0): Multiple red flags, immediate action required

    **Recommended Actions:**
    - ALLOW: Normal authentication, proceed
    - REQUIRE_2FA: Additional verification needed
    - BLOCK: Temporarily block authentication
    - RESET_PASSWORD: Force password reset due to compromise risk

    Provide your assessment with clear reasoning for the risk level and recommended action.
  "#
}

function FraudDetectionGemini(
  user_id: int,
  username: string,
  event_type: string,
  ip_address: string,
  user_agent: string,
  timestamp: string,
  recent_events: AuthEvent[]
) -> FraudAssessment {
  client Gemini

  prompt #"
    You are a cybersecurity expert analyzing authentication events for fraud detection.

    Analyze the following authentication event for fraud indicators:

    **Current Event:**
    - User ID: {{ user_id }}
    - Username: {{ username }}
    - Event Type: {{ event_type }}
    - IP Address: {{ ip_address }}
    - User Agent: {{ user_agent }}
    - Timestamp: {{ timestamp }}

    **Recent Event History (last 24 hours):**
    {% for event in recent_events %}
    - {{ event.event_type }} from {{ event.ip_address }} at {{ event.timestamp }}
    {% endfor %}

    **Analysis Criteria:**
    1. Geographic anomalies (IP location changes)
    2. Device fingerprint changes (user agent variations)
    3. Temporal patterns (unusual login times, rapid succession)
    4. Failed attempt frequency and patterns
    5. Velocity checks (multiple attempts from different IPs)
    6. Known attack patterns (brute force, credential stuffing)

    **Risk Assessment Guidelines:**
    - LOW (0.0-0.3): Normal behavior, no suspicious indicators
    - MEDIUM (0.3-0.7): Some anomalies detected, monitor closely
    - HIGH (0.7-1.0): Multiple red flags, immediate action required

    **Recommended Actions:**
    - ALLOW: Normal authentication, proceed
    - REQUIRE_2FA: Additional verification needed
    - BLOCK: Temporarily block authentication
    - RESET_PASSWORD: Force password reset due to compromise risk

    Provide your assessment with clear reasoning for the risk level and recommended action.
  "#
}

// Input schema for authentication events
class AuthEvent {
  event_type string
  ip_address string
  user_agent string
  timestamp string
  success bool
}

// Output schema for fraud assessment
class FraudAssessment {
  risk_level RiskLevel
  risk_score float // 0.0 to 1.0
  action RecommendedAction
  reason string
  confidence float // 0.0 to 1.0
  risk_factors string[] // List of detected risk indicators
}

enum RiskLevel {
  LOW
  MEDIUM
  HIGH
}

enum RecommendedAction {
  ALLOW
  REQUIRE_2FA
  BLOCK
  RESET_PASSWORD
}
