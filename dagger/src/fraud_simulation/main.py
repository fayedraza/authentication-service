"""Dagger module for fraud simulation."""
import dagger
from dagger import dag, function, object_type, Doc
from typing import Annotated

@object_type
class FraudSimulation:
    """A Dagger module to run fraud simulation pipelines."""
    @function
    async def run_fraud_sim(
        self,
        gemini_api_key: Annotated[dagger.Secret, Doc("Gemini API token")],
        groq_api_key: Annotated[dagger.Secret, Doc("Groq API token")],
    ) -> str:
        """
        Runs the fraud simulation pipeline with the provided AI API keys.
        """
        # Get the host directory (where dagger call is executed)
        # In Dagger Cloud, this will be the workspace directory.
        host_dir = dag.host().directory(".")

        # Define the base container with Python
        base = (
            dag.container()
            .from_("python:3.11-slim")
            .with_directory("/app", host_dir)
            .with_workdir("/app")
            .with_exec(["pip", "install", "pydantic"])
        )

        print("\n" + "="*50)
        print("🚀 STARTING DAGGER FRAUD SIMULATION (CLOUD/MODULE)")
        print("="*50 + "\n")

        # Step 1: Generate Accounts
        print("👉 Step 1: Generating Accounts...")
        step1 = base.with_exec(["python3", "fraud_simulation/generate_accounts.py"])

        # Step 2: Generate Logs
        print("👉 Step 2: Generating Logs...")
        step2 = step1.with_exec(["python3", "fraud_simulation/generate_logs.py"])

        # Step 3: Process Logs with Secrets
        print("👉 Step 3: Running Fraud Analysis Agent (Comparing Gemini & Groq)...")
        step3 = (
            step2
            .with_secret_variable("GEMINI_API_KEY", gemini_api_key)
            .with_secret_variable("GROQ_API_KEY", groq_api_key)
            .with_exec(["python3", "fraud_simulation/process_logs.py"])
        )

        # Step 4: Expose Output
        # This makes the results available via the Dagger API/UI

        # To make it "complete" the simulation and show status
        await step3.stdout()

        return "✅ Simulation complete! Results available in fraud_simulation_reports/summary.json"
