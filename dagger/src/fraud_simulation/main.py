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
    ) -> dagger.File:
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

        return step3.file("fraud_simulation_reports/iteration_latest.json")

    @function
    async def analyze_results(self, summary: dagger.File) -> str:
        return (
            dag.llm()
            .with_env(
                dag.env()
                .with_file_input("summary", summary, description="Fraud summary file")
                .with_string_output("insights", description="AI generated insights")
            )
            .with_prompt("""
            Review this fraud summary:
            $summary

            Identify top suspicious accounts and patterns. Suggest any actions or remediations.
            Highlight any unusual spikes or risk factors.
            """)
            .env().output("insights").as_string()
        )
