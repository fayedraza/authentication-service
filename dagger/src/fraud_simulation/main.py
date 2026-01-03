import dagger
from dagger import dag, function, object_type

@object_type
class FraudSimulation:
    @function
    async def run_fraud_sim(
        self,
        source: dagger.Directory,
        gemini_api_key: dagger.Secret,
        groq_api_key: dagger.Secret,
    ) -> str:
        """
        Runs the fraud simulation using the global Dagger context.
        """

        # Use the passed source directory instead of dag.host()
        base = (
            dag.container()
            .from_("python:3.11-slim")
            .with_directory("/app", source)
            .with_workdir("/app")
            .with_exec(["pip", "install", "pydantic"])
            .with_exec(["mkdir", "-p", "fraud_simulation"])
        )

        print("\n" + "=" * 50)
        print("🚀 STARTING DAGGER FRAUD SIMULATION")
        print("=" * 50 + "\n")

        # Paths are now relative to the root in dagger/src/fraud_simulation/
        sim_path = "dagger/src/fraud_simulation"

        step1 = base.with_exec(["python3", f"{sim_path}/generate_accounts.py"])
        step2 = step1.with_exec(["python3", f"{sim_path}/generate_logs.py"])
        step3 = (
            step2
            .with_secret_variable("GEMINI_API_KEY", gemini_api_key)
            .with_secret_variable("GROQ_API_KEY", groq_api_key)
            .with_exec(["python3", f"{sim_path}/process_logs.py"])
        )

        # Force streaming stdout to trigger execution
        await step3.stdout()

        return "✅ Simulation complete! Results available in fraud_simulation_reports/summary.json"
