import json
import random
from datetime import datetime, timedelta

def generate_logs(num_logs=20):
    try:
        with open("fraud_simulation/accounts.json", "r") as f:
            accounts = json.load(f)
    except FileNotFoundError:
        print("❌ accounts.json not found. Run generate_accounts.py first.")
        return

    logs = []

    # Simulate some signups first
    for _ in range(5):
        account = random.choice(accounts)
        logs.append({
            "user_id": account["user_id"],
            "event_type": "signup",
            "tier": account["tier"],
            "login_time": datetime.now().strftime("%H:%M")
        })

    for _ in range(num_logs):
        account = random.choice(accounts)
        is_suspicious = random.random() < 0.3 # 30% chance of suspicious activity

        event_type = "login"
        login_time = datetime.now().strftime("%H:%M")

        if is_suspicious:
            # Simulate anomalies: odd hours
            login_time = f"{random.randint(0, 4):02d}:{random.randint(0, 59):02d}" # Late night

        logs.append({
            "user_id": account["user_id"],
            "event_type": event_type,
            "tier": account["tier"],
            "login_time": login_time
        })

    with open("fraud_simulation/logs.json", "w") as f:
        json.dump(logs, f, indent=2)
    print(f"✅ Generated {len(logs)} login logs.")

if __name__ == "__main__":
    generate_logs()
