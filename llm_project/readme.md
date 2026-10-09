esQAI --- AI Cloud Reliability Assistant
ResQAI is a starter project that analyzes cloud reliability metrics and
logs, uses an LLM to explain likely causes, and creates a cautious
remediation plan. The current implementation analyzes data supplied by
the caller; it does not automatically monitor a cloud account or
execute infrastructure changes.
Current workflow
1. A caller sends cloud metrics and optional logs.
2. anomaly.py checks metrics against simple thresholds.
3. llm_analyzer.py sends metrics, logs, and detected anomalies to the
   OpenAI API.
4. The LLM returns a JSON incident analysis.
5. remediation.py turns detected anomalies and root-cause hypotheses
   into an investigation plan.
6. The backend can expose this workflow through a FastAPI endpoint.
Suggested project structure
llm_project/
├── backend/
│   └── main.py              # FastAPI entry point (create if needed)
├── anomaly.py               # Rule-based anomaly detection
├── llm_analyzer.py          # Direct LLM analysis; no RAG
├── remediation.py           # Safe, non-executing action plan
├── .env                     # Local API key; never commit this
├── .gitignore
├── requirements.txt
└── README.md
Keep your actual existing filenames and folders if they differ. If your
Python modules are in the project root, backend/main.py can import
them when you launch Uvicorn from the project root.
Requirements
- Python 3.10 or later recommended.
- An OpenAI API key with API access enabled. ChatGPT subscription
  billing and API billing are separate.
- Internet access for OpenAI API calls.
Install dependencies from the project root:
python -m pip install fastapi uvicorn openai python-dotenv
Optionally save installed dependencies:
python -m pip freeze > requirements.txt
Environment configuration
Create .env in the project root, beside anomaly.py and
llm_analyzer.py:
OPENAI_API_KEY=put_your_new_api_key_here
Do not add quotes or spaces around =. Do not share the key, place it
in source code, or commit .env to GitHub. If a key was exposed in
chat, a screenshot, or a repository, revoke it and create a replacement.
A suitable .gitignore is:
.env
.venv/
venv/
__pycache__/
*.py[cod]
chroma_db/
Backend integration
The backend should import the existing analysis functions and expose
them through an HTTP endpoint. The frontend or another service sends
JSON to the endpoint; FastAPI calls the Python functions and returns the
report.
Create backend/main.py:
from typing import Any

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

from anomaly import detect_anomalies
from llm_analyzer import analyze_incident
from remediation import create_remediation_plan

app = FastAPI(
    title="ResQAI API",
    description="LLM-assisted cloud incident analysis",
    version="0.1.0",
)


class IncidentRequest(BaseModel):
    metrics: dict[str, float] = Field(
        description="Numeric cloud metrics, e.g. cpu_percent and latency_ms"
    )
    logs: list[str] = Field(default_factory=list)


@app.get("/health")
def health():
    return {"status": "ok", "service": "ResQAI"}


@app.post("/analyze")
def analyze(request: IncidentRequest) -> dict[str, Any]:
    try:
        # The LLM analyzer performs rule-based detection internally.
        report = analyze_incident(request.metrics, request.logs)

        # Attach the safe investigation plan.
        report["remediation_plan"] = create_remediation_plan(report)
        return report

    except Exception as exc:
        # Do not return secrets or internal tracebacks to API callers.
        raise HTTPException(
            status_code=502,
            detail="Incident analysis failed. Check the backend logs.",
        ) from exc
Start the API
From the project root, run:
python -m uvicorn backend.main:app --reload
If Python cannot import backend.main, make sure backend/main.py
exists and add an empty backend/__init__.py file if needed. Run the
command from the project root, not from inside backend.
Open the interactive API docs in a browser:
- http://127.0.0.1:8000/docs
- Health check: http://127.0.0.1:8000/health
In /docs, open POST /analyze → Try it out and send an example:
{
  "metrics": {
    "cpu_percent": 35,
    "memory_percent": 96,
    "latency_ms": 2800,
    "error_rate_percent": 8,
    "database_failures": 3
  },
  "logs": [
    "Database connection timeout",
    "HTTP 503 Service Unavailable"
  ]
}
The request should return an incident report from the LLM plus a
remediation plan. This makes an OpenAI API request and may incur API
charges.
How another backend team member can integrate it
The backend member does not need to rewrite the LLM logic. They can call
the endpoint:
const response = await fetch("http://127.0.0.1:8000/analyze", {
  method: "POST",
  headers: { "Content-Type": "application/json" },
  body: JSON.stringify({
    metrics: {
      cpu_percent: 35,
      memory_percent: 96,
      latency_ms: 2800,
      error_rate_percent: 8,
      database_failures: 3
    },
    logs: ["Database connection timeout", "HTTP 503 Service Unavailable"]
  })
});

const report = await response.json();
console.log(report);
For a teammate's computer, 127.0.0.1 refers to that teammate's own
computer. Use the backend host's reachable address during development,
and configure CORS if a browser-based frontend runs on a different
origin. Do not expose a development server publicly without
authentication, rate limiting, and appropriate deployment controls.
Safety and limitations
- ResQAI only analyzes metrics and logs supplied to it; cloud
  monitoring integrations are not included yet.
- Root causes produced by the LLM are hypotheses, not confirmed facts.
- Remediation recommendations are not executed. Require human review
  before any real infrastructure change.
- Add authentication, request limits, logging, monitoring, and
  stronger input validation before production deployment.
- Avoid sending secrets, personal data, access tokens, or unrelated
  sensitive log contents to the LLM.
Troubleshooting
OPENAI_API_KEY missing - Confirm .env is at the project root,
beside llm_analyzer.py. - Confirm the spelling is exactly
OPENAI_API_KEY. - Restart the terminal after changing environment
configuration if needed. - Never print the key to debug it.
ModuleNotFoundError - Install dependencies using the same Python
interpreter that runs the server. - Run Uvicorn from the project root. -
Ensure backend/main.py and the root-level modules match the structure
above.
OpenAI authentication or quota error - Confirm the key is valid and
active. - Confirm API access and billing/quota are configured on the
OpenAI platform. ChatGPT plans do not automatically include API credits.
API returns 502 - Check the backend terminal for the underlying
error. - Do not return raw exceptions or credentials to API clients.
Roadmap
- [ ] Verify rule-based anomaly detection with test cases.
- [ ] Test LLM output and handle invalid or empty responses.
- [ ] Add FastAPI endpoint and API tests.
- [ ] Add authentication and request limits.
- [ ] Connect a real metrics/log source (for example, a cloud
  monitoring provider).
- [ ] Build a dashboard for incidents and remediation plans.
- [ ] Add human-approved remediation workflows only after review and
  safeguards.