
import json
import os
from pathlib import Path

from dotenv import load_dotenv
from openai import OpenAI

from anomaly import detect_anomalies

# Load the API key from the project-root .env
PROJECT_ROOT = Path(__file__).resolve().parent
load_dotenv(PROJECT_ROOT / ".env")

api_key = os.getenv("OPENAI_API_KEY")

if not api_key:
    raise ValueError("OPENAI_API_KEY missing. Check your .env file.")

client = OpenAI(api_key=api_key.strip())


def analyze_incident(metrics: dict, logs: list[str] | None = None):
    # Step 1: Detect anomalies using Python
    anomalies = detect_anomalies(metrics)

    # Step 2: Prepare evidence for the LLM
    incident_data = {
        "metrics": metrics,
        "logs": logs or [],
        "detected_anomalies": anomalies,
    }

    # Step 3: Ask the LLM to explain the incident
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {
                "role": "system",
                "content": (
                    "You are ResQAI, a cloud reliability assistant. "
                    "Analyze the supplied metrics, logs, and detected "
                    "anomalies. Explain likely root causes, severity, "
                    "and safe investigation steps. Distinguish facts "
                    "from hypotheses. Do not claim actions were executed. "
                    "Require human approval for infrastructure changes. "
                    "Return valid JSON with keys: summary, severity, "
                    "likely_root_causes, recommended_actions, "
                    "requires_human_approval."
                ),
            },
            {
                "role": "user",
                "content": json.dumps(incident_data),
            },
        ],
        response_format={"type": "json_object"},
        temperature=0.2,
    )

    result = response.choices[0].message.content
    report = json.loads(result)

    # Keep Python's detected evidence in the final report
    report["detected_anomalies"] = anomalies
    report["execution_mode"] = "dry_run"
    report["executed"] = False

    return report


if __name__ == "__main__":
    sample_metrics = {
        "cpu_percent": 35,
        "memory_percent": 96,
        "latency_ms": 2800,
        "error_rate_percent": 8,
        "database_failures": 3,
    }

    sample_logs = [
        "Database connection timeout",
        "HTTP 503 Service Unavailable",
    ]

    report = analyze_incident(sample_metrics, sample_logs)
    print(json.dumps(report, indent=2))

