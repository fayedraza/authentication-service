// BAML configuration for Fraud Detection Agent Simulation

class LoginInput {
  user_id string
  tier string
  login_time string
}

class FraudOutput {
  fraud_score_ai float
  fraud_score_rule float
  is_anomaly bool
  execution_mode string
  reasons string[]
}

function AnalyzeFraud(input: LoginInput) -> FraudOutput {
  client Gemini
  prompt #"
    Analyze the following login event for potential fraud.

    User ID: {{ input.user_id }}
    Tier: {{ input.tier }}
    Login Time: {{ input.login_time }}

    Guidelines:
    - If tier is 'dev', primarily use rule-based logic (set fraud_score_ai to 0.0).
    - If tier is 'pro', use full AI analysis to set fraud_score_ai.
    - is_anomaly should be true if either score > 0.7.
    - reasons should list specific triggers (e.g., "Late login", "Suspicious pattern").

    Return a JSON object conforming to the FraudOutput schema.

    {{ ctx.output_format }}
  "#
}
