import anyio
import sys
import os

# Add the project root to sys.path so we can import the pipeline
sys.path.append(os.getcwd())

from fraud_simulation.fraud_agent_pipeline import analyze_build_failure

async def main():
    # A mock error that looks like a real pipeline failure
    mock_error = """
    Error: process "python3 fraud_simulation/process_logs.py" did not complete successfully
    Exit code: 1
    Stderr: Traceback (most recent call last):
      File "fraud_simulation/process_logs.py", line 45, in <module>
        with open("fraud_simulation/logs.json", "r") as f:
    FileNotFoundError: [Errno 2] No such file or directory: 'fraud_simulation/logs.json'
    """

    print("🚀 Running Manual Test for AI Analysis Agent...")
    print(f"Submitting mock error:\n{mock_error}")

    await analyze_build_failure(mock_error)

if __name__ == "__main__":
    anyio.run(main)
