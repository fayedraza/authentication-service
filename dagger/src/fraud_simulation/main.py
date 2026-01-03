# dagger/module.py
import dagger
from dagger import function

@function
async def run_fraud_sim(
    gemini_api_key: dagger.Secret,
    groq_api_key: dagger.Secret,
) -> str:
    """
    Runs the fraud simulation using the global Dagger context.
    """

    # Use global `dagger` / `dag`, not self
    host_dir = dagger.host().directory(".")

    base = (
        dagger.container()
        .from_("python:3.11-slim")
        .with_directory("/app", host_dir)
        .with_workdir("/app")
        .with_exec(["pip", "install", "pydantic"])
    )

    print("\n" + "=" * 50)
    print("🚀 STARTING DAGGER FRAUD SIMULATION")
    print("=" * 50 + "\n")

    step1 = base.with_exec(["python3", "fraud_simulation/generate_accounts.py"])
    step2 = step1.with_exec(["python3", "fraud_simulation/generate_logs.py"])
    step3 = (
        step2
        .with_secret_variable("GEMINI_API_KEY", gemini_api_key)
        .with_secret_variable("GROQ_API_KEY", groq_api_key)
        .with_exec(["python3", "fraud_simulation/process_logs.py"])
    )

    # Force streaming stdout to trigger execution
    await step3.stdout()

    return "✅ Simulation complete! Results available in fraud_simulation_reports/summary.json"
