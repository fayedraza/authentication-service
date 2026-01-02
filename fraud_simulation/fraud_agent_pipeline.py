import sys
import anyio
import dagger
import os
from datetime import datetime
import json

from dagger import dag

async def run_pipeline():
    # Configure Dagger client
    cfg = dagger.Config(log_output=sys.stdout)

    async with dagger.connection(cfg):
        # Get the host directory
        host_dir = dag.host().directory(".")

        # Define the base container with Python
        # We'll use this to run our simulation scripts
        base = (
            dag.container()
            .from_("python:3.11-slim")
            .with_directory("/app", host_dir)
            .with_workdir("/app")
            # In a real scenario, we'd install baml-py here
            # For the simulation, process_logs.py handles its own logic
            .with_exec(["pip", "install", "pydantic"])
        )

        print("\n" + "="*50)
        print("🚀 STARTING DAGGER FRAUD SIMULATION PIPELINE")
        print("="*50 + "\n")

        # Step 1: Generate Accounts
        print("👉 Step 1: Generating Accounts...")
        step1 = base.with_exec(["python3", "fraud_simulation/generate_accounts.py"])

        # Step 2: Generate Logs
        print("👉 Step 2: Generating Logs...")
        step2 = step1.with_exec(["python3", "fraud_simulation/generate_logs.py"])

        # Step 3: Process Logs (Fraud Analysis with Gemini and Groq comparison)
        print("👉 Step 3: Running Fraud Analysis Agent (Comparing Gemini & Groq)...")
        step3 = (
            step2.with_env_variable("GEMINI_API_KEY", os.environ.get("GEMINI_API_KEY", ""))
            .with_env_variable("GROQ_API_KEY", os.environ.get("GROQ_API_KEY", ""))
            .with_exec(["python3", "fraud_simulation/process_logs.py"])
        )

        # Step 4: Capture Results from Container
        print("👉 Step 4: Capturing Iteration Results...")
        results_contents = await step3.file("fraud_simulation_reports/iteration_latest.json").contents()

        # Save results locally for persistence and summary generation
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        res_dir = "fraud_simulation_reports"
        iter_dir = os.path.join(res_dir, "iterations")
        os.makedirs(iter_dir, exist_ok=True)

        iteration_file = f"iteration_{timestamp}.json"
        local_path = os.path.join(iter_dir, iteration_file)

        with open(local_path, "w") as f:
            f.write(results_contents)

        print(f"✅ Pipeline Iteration Complete.")
        print(f"📄 Results saved to: {local_path}")

        # Update the aggregate summary report
        update_summary(res_dir)

def update_summary(res_dir):
    # Find all iteration files in the iterations subdirectory
    iter_dir = os.path.join(res_dir, "iterations")
    files = [f for f in os.listdir(iter_dir) if f.startswith("iteration_") and f.endswith(".json")]

    total_logins = 0
    total_suspicious = 0
    total_accounts = 0
    account_stats = {} # user_id -> {total_score, count, alerts}

    for f in files:
        file_path = os.path.join(iter_dir, f)
        try:
            with open(file_path, "r") as json_file:
                data = json.load(json_file)
                total_logins += data.get("total_logins", 0)
                total_suspicious += data.get("suspicious_logins", 0)
                total_accounts += data.get("accounts_created", 0)

                for detail in data.get("details", []):
                    user_id = detail.get("user_id")
                    score = max(detail.get("fraud_score_ai", 0), detail.get("fraud_score_rule", 0))
                    is_anomaly = detail.get("is_anomaly", False)

                    if user_id not in account_stats:
                        account_stats[user_id] = {"total_score": 0.0, "count": 0, "alerts": 0}

                    account_stats[user_id]["total_score"] += score
                    account_stats[user_id]["count"] += 1
                    if is_anomaly:
                        account_stats[user_id]["alerts"] += 1
        except Exception as e:
            print(f"Warning: Could not read {f}: {e}")

    # Calculate per account metrics
    account_metrics = []
    for user_id, stats in account_stats.items():
        account_metrics.append({
            "user_id": user_id,
            "average_score": round(stats["total_score"] / stats["count"], 2) if stats["count"] > 0 else 0,
            "total_alerts": stats["alerts"]
        })

    # Sort by score descending to highlight suspicious accounts
    account_metrics.sort(key=lambda x: x["average_score"], reverse=True)

    summary = {
        "report_type": "Aggregate Fraud Simulation Summary",
        "last_updated": datetime.now().isoformat(),
        "total_iterations": len(files),
        "total_accounts_created": total_accounts,
        "total_logins_processed": total_logins,
        "total_suspicious_detected": total_suspicious,
        "average_fraud_score_per_account": [
            {"user_id": m["user_id"], "score": m["average_score"]} for m in account_metrics
        ],
        "total_alerts_per_account": [
            {"user_id": m["user_id"], "alerts": m["total_alerts"]} for m in account_metrics
        ],
        "status": "Healthy"
    }

    summary_path = os.path.join(res_dir, "summary.json")
    with open(summary_path, "w") as f:
        json.dump(summary, f, indent=2)

    print("\n" + "-"*30)
    print("📊 FINAL SUMMARY REPORT")
    print(f"Iterations: {len(files)}")
    print(f"Accounts Created: {total_accounts}")
    print(f"Total Logins: {total_logins}")
    print(f"Suspicious Detected: {total_suspicious}")
    print(f"Top Suspicious Account: {account_metrics[0]['user_id'] if account_metrics else 'N/A'} (Score: {account_metrics[0]['average_score'] if account_metrics else 0})")
    print(f"Report Location: {summary_path}")
    print("-"*30 + "\n")

async def analyze_build_failure(error):
    """
    Uses Dagger's built-in AI Agent (LLM) to analyze pipeline failures.
    """
    print(f"\n🧠 Dagger AI Agent: Analyzing pipeline failure...")

    cfg = dagger.Config(log_output=sys.stdout)
    async with dagger.connection(cfg):
        try:
            # Define the assignment context
            env = (
                dag.env()
                .with_string_input("error_log", str(error), "The error message or stack trace reported by the pipeline")
                .with_string_output("fix_suggestion", "A detailed analysis and proposed fix for the error")
            )

            # Define the AI Agent instructions
            work = (
                dag.llm()
                .with_env(env)
                .with_prompt(
                    """
                    You are an expert CI/CD and Python developer specializing in Dagger pipelines.
                    The simulation pipeline just failed.

                    Error Log:
                    $error_log

                    Task:
                    1. Identify the root cause of the failure.
                    2. Suggest a specific code or environment fix.
                    3. Keep it concise.

                    Write your full response into the 'fix_suggestion' output.
                    """
                )
            )

            # Execute and retrieve the result
            suggestion = await work.env().output("fix_suggestion").as_string()

            print("\n" + "🤖 BuildFix AI Agent Analysis " + "━"*20)
            print(suggestion)
            print("━"*50 + "\n")

        except Exception as e:
            print(f"⚠️ BuildFix Agent could not complete analysis: {e}")
            print("💡 Tip: Ensure an LLM provider is configured (e.g., set OPENAI_API_KEY).")

if __name__ == "__main__":
    try:
        anyio.run(run_pipeline)
    except Exception as e:
        print(f"❌ Pipeline failed: {e}")
        # Run AI analysis on the failure
        anyio.run(analyze_build_failure, e)
        sys.exit(1)
