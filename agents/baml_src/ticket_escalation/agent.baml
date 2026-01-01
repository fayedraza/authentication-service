// Ticket Escalation BAML Agent
// Analyzes support ticket content to determine priority and escalation requirements

function TicketEscalation(
  ticket_id: int,
  title: string,
  description: string,
  owner_tier: string,
  created_at: string,
  owner_history: OwnerContext
) -> TicketAnalysis {
  client Groq

  prompt #"
    You are a customer support expert analyzing support tickets for priority classification and escalation decisions.

    Analyze the following support ticket:

    **Ticket Information:**
    - Ticket ID: {{ ticket_id }}
    - Title: {{ title }}
    - Description: {{ description }}
    - Customer Tier: {{ owner_tier }}
    - Created At: {{ created_at }}

    **Customer Context:**
    - Previous Tickets: {{ owner_history.previous_ticket_count }}
    - Account Age: {{ owner_history.account_age_days }} days
    - Last Ticket Date: {{ owner_history.last_ticket_date }}
    - Resolution History: {{ owner_history.avg_resolution_time_hours }} hours average

    **Tier-Based Prioritization Rules (PRIMARY):**
    1. **Dev Tier**: Maximum priority is MEDIUM. Do not escalate unless the issue is a verifiable Security Breach affecting the platform. Response time SLA is doubled.
    2. **Pro Tier**: Priority is evaluated based on the criteria below. Pro users receive preferential handling for High/Critical issues.

    **Classification Criteria:**

    **Priority Levels:**
    - CRITICAL: Security breaches, system down, data loss, payment issues (Pro Only, unless global security risk)
    - HIGH: Authentication failures, integration broken (Pro Only)
    - MEDIUM: Feature requests, minor bugs, configuration help (Dev Max)
    - LOW: General questions, documentation requests, cosmetic issues

    **Category Classification:**
    - SECURITY: Authentication, authorization, data breaches, suspicious activity
    - INTEGRATION: API issues, SDK problems, webhook failures
    - BILLING: Payment problems, subscription issues, invoicing
    - TECHNICAL: Bugs, performance issues, configuration problems
    - GENERAL: Questions, feature requests, documentation

    **Escalation Rules:**
    - Always escalate CRITICAL priority tickets
    - Escalate HIGH priority tickets for Pro-tier customers
    - Escalate if Pro customer has had 3+ tickets in last 30 days
    - Escalate security-related issues regardless of priority
    - Escalate if previous tickets took >48 hours to resolve

    **Response Time SLA (hours):**
    - CRITICAL: 1 hour (Pro), 2 hours (Dev)
    - HIGH: 4 hours (Pro), 8 hours (Dev)
    - MEDIUM: 24 hours (Pro), 48 hours (Dev)
    - LOW: 48 hours (Pro), 72 hours (Dev)

    **Keywords to Watch:**
    - Security: "hack", "breach", "unauthorized", "suspicious", "compromised"
    - Critical: "down", "broken", "not working", "urgent", "emergency"
    - Integration: "API", "webhook", "SDK", "integration", "connection"
    - Billing: "payment", "charge", "invoice", "subscription", "billing"

    Provide a comprehensive analysis with clear reasoning for the priority, category, and escalation decision. Ensure the reasoning explicitly mentions the user's tier impact on the priority decision.
  "#
}

function TicketEscalationGemini(
  ticket_id: int,
  title: string,
  description: string,
  owner_tier: string,
  created_at: string,
  owner_history: OwnerContext
) -> TicketAnalysis {
  client Gemini

  prompt #"
    You are a customer support expert analyzing support tickets for priority classification and escalation decisions.

    Analyze the following support ticket:

    **Ticket Information:**
    - Ticket ID: {{ ticket_id }}
    - Title: {{ title }}
    - Description: {{ description }}
    - Customer Tier: {{ owner_tier }}
    - Created At: {{ created_at }}

    **Customer Context:**
    - Previous Tickets: {{ owner_history.previous_ticket_count }}
    - Account Age: {{ owner_history.account_age_days }} days
    - Last Ticket Date: {{ owner_history.last_ticket_date }}
    - Resolution History: {{ owner_history.avg_resolution_time_hours }} hours average

    **Tier-Based Prioritization Rules (PRIMARY):**
    1. **Dev Tier**: Maximum priority is MEDIUM. Do not escalate unless the issue is a verifiable Security Breach affecting the platform. Response time SLA is doubled.
    2. **Pro Tier**: Priority is evaluated based on the criteria below. Pro users receive preferential handling for High/Critical issues.

    **Classification Criteria:**

    **Priority Levels:**
    - CRITICAL: Security breaches, system down, data loss, payment issues (Pro Only, unless global security risk)
    - HIGH: Authentication failures, integration broken (Pro Only)
    - MEDIUM: Feature requests, minor bugs, configuration help (Dev Max)
    - LOW: General questions, documentation requests, cosmetic issues

    **Category Classification:**
    - SECURITY: Authentication, authorization, data breaches, suspicious activity
    - INTEGRATION: API issues, SDK problems, webhook failures
    - BILLING: Payment problems, subscription issues, invoicing
    - TECHNICAL: Bugs, performance issues, configuration problems
    - GENERAL: Questions, feature requests, documentation

    **Escalation Rules:**
    - Always escalate CRITICAL priority tickets
    - Escalate HIGH priority tickets for Pro-tier customers
    - Escalate if Pro customer has had 3+ tickets in last 30 days
    - Escalate security-related issues regardless of priority
    - Escalate if previous tickets took >48 hours to resolve

    **Response Time SLA (hours):**
    - CRITICAL: 1 hour (Pro), 2 hours (Dev)
    - HIGH: 4 hours (Pro), 8 hours (Dev)
    - MEDIUM: 24 hours (Pro), 48 hours (Dev)
    - LOW: 48 hours (Pro), 72 hours (Dev)

    **Keywords to Watch:**
    - Security: "hack", "breach", "unauthorized", "suspicious", "compromised"
    - Critical: "down", "broken", "not working", "urgent", "emergency"
    - Integration: "API", "webhook", "SDK", "integration", "connection"
    - Billing: "payment", "charge", "invoice", "subscription", "billing"

    Provide a comprehensive analysis with clear reasoning for the priority, category, and escalation decision. Ensure the reasoning explicitly mentions the user's tier impact on the priority decision.
  "#
}

// Input schema for customer context
class OwnerContext {
  previous_ticket_count int
  account_age_days int
  last_ticket_date string?
  avg_resolution_time_hours float
  tier_upgrade_date string?
  total_api_calls_last_month int
}

// Output schema for ticket analysis
class TicketAnalysis {
  priority Priority
  category Category
  escalate bool
  escalation_reason string?
  suggested_response_time int // hours
  tags string[]
  urgency_score float // 0.0 to 1.0
  customer_impact_level ImpactLevel
  recommended_assignee AssigneeType
}

enum Priority {
  LOW
  MEDIUM
  HIGH
  CRITICAL
}

enum Category {
  SECURITY
  INTEGRATION
  BILLING
  TECHNICAL
  GENERAL
}

enum ImpactLevel {
  MINIMAL
  MODERATE
  SIGNIFICANT
  SEVERE
}

enum AssigneeType {
  TIER1_SUPPORT
  TIER2_TECHNICAL
  SECURITY_TEAM
  BILLING_SPECIALIST
  ENGINEERING_TEAM
}
