import json
import os
import random
from datetime import datetime

# Rule-based logic for simulation (Updated: only basic patterns)
def run_rules(log):
    reasons = []
    score = 0.0

    # Check for odd hours (12 AM to 5 AM)
    login_time = log.get("login_time", "12:00")
    try:
        hour = int(login_time.split(":")[0])
        if 0 <= hour <= 5:
            reasons.append(f"[Rule] Suspicious login time: {login_time}")
            score += 0.5
    except (ValueError, IndexError):
        pass

    return min(score, 1.0), reasons

async def process_logs():
    try:
        with open("fraud_simulation/logs.json", "r") as f:
            logs = json.load(f)
    except FileNotFoundError:
        print("❌ logs.json not found. Run generate_logs.py first.")
        return

    results = []
    total_score = 0
    suspicious_count = 0
    accounts_created = 0

    ai_models = {
        "Gemini": os.environ.get("AI_MODEL_GEMINI", "Gemini-1.5-Pro"),
        "Groq": os.environ.get("AI_MODEL_GROQ", "Groq-Llama-3")
    }

    for log in logs:
        if log.get("event_type") == "signup":
            accounts_created += 1
            continue

        rule_score, rule_reasons = run_rules(log)

        # Run simulation for both models
        model_results = {}
        for provider, model_name in ai_models.items():
            ai_score = 0.0
            ai_reasons = []

            # Pro users trigger AI logic
            if log["tier"] == "pro":
                if rule_score > 0.4:
                    # Slightly different logic/sensitivity per model
                    noise = random.uniform(0.0, 0.2)
                    multiplier = 1.2 if provider == "Gemini" else 1.15
                    ai_score = min(rule_score * multiplier + noise, 1.0)

                    if ai_score > 0.7:
                        reason_msg = "detected anomalous login pattern" if provider == "Gemini" else "flagged unusual activity signature"
                        ai_reasons.append(f"[{model_name}] {reason_msg}")
                else:
                    ai_score = random.uniform(0.0, 0.3)

            model_results[provider] = {
                "score": round(ai_score, 2),
                "reasons": ai_reasons,
                "model": model_name
            }

        # For backward compatibility with summary scripts, we use Gemini as the "primary" AI score
        primary_ai_score = model_results["Gemini"]["score"]
        is_anomaly = (primary_ai_score > 0.7) or (rule_score > 0.7)

        if is_anomaly:
            suspicious_count += 1

        # Combine reasons for the "reasons" field (Gemini + Rule)
        final_reasons = list(set(rule_reasons + model_results["Gemini"]["reasons"]))

        result = {
            "user_id": log["user_id"],
            "tier": log["tier"],
            "fraud_score_ai": primary_ai_score, # Legacy field
            "fraud_score_rule": round(rule_score, 2),
            "is_anomaly": is_anomaly,
            "login_time": log.get("login_time", "unknown"),
            "comparison": {
                "gemini": model_results["Gemini"],
                "groq": model_results["Groq"]
            },
            "reasons": final_reasons
        }
        results.append(result)
        total_score += max(primary_ai_score, rule_score)

    avg_score = total_score / len(results) if results else 0

    output = {
        "timestamp": datetime.now().isoformat(),
        "accounts_created": accounts_created,
        "total_logins": len(results),
        "normal_logins": len(results) - suspicious_count,
        "suspicious_logins": suspicious_count,
        "average_score": round(avg_score, 2),
        "details": results
    }

    os.makedirs("fraud_simulation_reports", exist_ok=True)
    with open("fraud_simulation_reports/iteration_latest.json", "w") as f:
        json.dump(output, f, indent=2)

    print(f"✅ Processed {len(logs)} logs. Suspicious: {suspicious_count}")

if __name__ == "__main__":
    import asyncio
    asyncio.run(process_logs())
