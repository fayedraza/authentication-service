# Dagger Fraud Simulation Workflow

This directory contains the [Dagger](https://dagger.io) module for the Fraud Simulation and AI Analysis pipeline.

## Purpose

The Dagger Workflow Pipeline automates the end-to-end fraud detection simulation:
1.  **Generation**: Spawns mock user accounts and login login events.
2.  **Simulation**: Processes logs through rule-based and AI-powered detections (Gemini & Groq).
3.  **Aggregation**: Summarizes results with per-account fraud scores and alerts.
4.  **AI Insights**: Analyzes the final summary report using Dagger's AI Agent to provide high-level insights and patterns.

Using Dagger ensures this pipeline runs consistently across local development and GitHub Actions by encapsulating the environment in containers.

## Local Usage

### 1. View Available Functions

To see the available functions and their documentation:

```bash
dagger functions
```

Or for detailed help on a specific function:

```bash
dagger call run-fraud-sim --help
```

### 2. Run Fraud Simulation

To run the full simulation and export the results to a local file:

```bash
# Ensure your API keys are set as environment variables
export GEMINI_API_KEY="your_key_here"
export GROQ_API_KEY="your_key_here"

dagger call run-fraud-sim \
  --source . \
  --gemini-api-key env:GEMINI_API_KEY \
  --groq-api-key env:GROQ_API_KEY \
  export --path results/summary.json
```

**Note:** `env:GEMINI_API_KEY` tells Dagger to read the value from your host's environment variable and pass it securely as a secret.

### 3. Run AI Result Analysis

To generate AI insights from an existing summary report:

```bash
dagger call analyze-results --summary results/summary.json > results/insights.txt
```

This command uses the `analyze_results` function which leverages Dagger's built-in LLM capabilities to review the summary and suggest remediations.

## Automated Execution (CI)

This module is triggered automatically via GitHub Actions in [.github/workflows/dagger-fraud-sim.yml](file:///Users/fayedraza/Authenication%20Service/.github/workflows/dagger-fraud-sim.yml) whenever the main CI pipeline completes successfully.
