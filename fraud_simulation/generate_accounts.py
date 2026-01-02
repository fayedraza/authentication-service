import json
import random

def generate_accounts(num_dev=10, num_pro=10):
    accounts = []

    # Dev tier accounts
    for i in range(num_dev):
        accounts.append({
            "user_id": f"dev_{i:03d}",
            "username": f"dev_user_{i}",
            "tier": "dev"
        })

    # Pro tier accounts
    for i in range(num_pro):
        accounts.append({
            "user_id": f"pro_{i:03d}",
            "username": f"pro_user_{i}",
            "tier": "pro"
        })

    with open("fraud_simulation/accounts.json", "w") as f:
        json.dump(accounts, f, indent=2)
    print(f"✅ Generated {len(accounts)} accounts (Dev: {num_dev}, Pro: {num_pro})")

if __name__ == "__main__":
    generate_accounts()
