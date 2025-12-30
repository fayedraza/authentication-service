// BAML schema for fraud detection agent
// This defines the input/output structure and prompt for AI-powered fraud analysis

class LoginEvent {
  user_id int
  username string
  ip_address string?
  user_agent string?
  timestamp string
  event_type string
  failed_attempts_5min int
  failed_2fa_attempts_5min int
  ip_changed bool
  user_agent_changed bool
}

class FraudAssessment {
  risk_score float
  alert bool
  reason string
  confidence float
}

function FraudCheck(event: LoginEvent) -> FraudAssessment {
  client GPT4
  prompt #"
    Analyze this authentication event for signs of fraudulent activity.

    Event Details:
    - User ID: {{ event.user_id }}
    - Username: {{ event.username }}
    - Event Type: {{ event.event_type }}
    - IP Address: {{ event.ip_address or "unknown" }}
    - User Agent: {{ event.user_agent or "unknown" }}
    - Timestamp: {{ event.timestamp }}

    Recent Activity Indicators:
    - Failed login attempts in last 5 minutes: {{ event.failed_attempts_5min }}
    - Failed 2FA attempts in last 5 minutes: {{ event.failed_2fa_attempts_5min }}
    - IP address changed from previous login: {{ event.ip_changed }}
    - User agent changed from previous login: {{ event.user_agent_changed }}

    Consider the following when assessing fraud risk:
    1. Multiple failed authentication attempts may indicate brute force attacks
    2. Failed 2FA attempts are particularly suspicious as they suggest compromised credentials
    3. Changes in IP address or user agent could indicate account takeover
    4. Unusual timing patterns or rapid sequences of events
    5. The combination of multiple risk factors increases overall risk

    Provide a risk score from 0.0 (no risk) to 1.0 (high risk).
    Set alert to true if the risk score is 0.7 or higher.
    Provide a clear, concise explanation of your reasoning in the reason field.
    Set confidence to a value between 0.0 and 1.0 indicating your confidence in the assessment.

    Return your assessment as a JSON object with risk_score, alert, reason, and confidence fields.
  "#
}
