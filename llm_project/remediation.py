
from datetime import datetime, timezone


def create_remediation_plan(incident_report: dict) -> dict:
    """Create a safe, approval-based remediation plan."""

    anomalies = incident_report.get("detected_anomalies", [])
    root_causes = incident_report.get("likely_root_causes", [])

    actions = []

    # Recommend investigations based on detected evidence
    for anomaly in anomalies:
        text = anomaly.lower()

        if "memory" in text:
            actions.append({
                "action": "Investigate memory usage",
                "steps": [
                    "Inspect memory utilization over time",
                    "Check for memory leaks and worker restarts",
                    "Review application memory limits"
                ],
                "approval_required": False
            })

        elif "cpu" in text:
            actions.append({
                "action": "Investigate CPU utilization",
                "steps": [
                    "Inspect CPU usage by process",
                    "Review traffic and workload spikes",
                    "Check recent deployments"
                ],
                "approval_required": False
            })

        elif "latency" in text:
            actions.append({
                "action": "Investigate API latency",
                "steps": [
                    "Inspect request latency percentiles",
                    "Review application and upstream timings",
                    "Check database query performance"
                ],
                "approval_required": False
            })

        elif "error" in text or "503" in text:
            actions.append({
                "action": "Investigate application errors",
                "steps": [
                    "Inspect logs around failed requests",
                    "Check application health",
                    "Review recent deployments"
                ],
                "approval_required": False
            })

        elif "database" in text:
            actions.append({
                "action": "Investigate database connectivity",
                "steps": [
                    "Check database health and availability",
                    "Inspect connection timeout logs",
                    "Review connection pool utilization"
                ],
                "approval_required": False
            })

    # Remove duplicate recommendations
    unique_actions = []
    seen = set()

    for action in actions:
        if action["action"] not in seen:
            unique_actions.append(action)
            seen.add(action["action"])

    if not unique_actions:
        unique_actions.append({
            "action": "Review incident evidence",
            "steps": [
                "Review supplied metrics and logs",
                "Verify service health",
                "Collect additional evidence if needed"
            ],
            "approval_required": False
        })

    # Actual changes always require human approval
    return {
        "plan_id": "RSQ-PLAN-" + datetime.now(
            timezone.utc
        ).strftime("%Y%m%d%H%M%S"),
        "created_at": datetime.now(timezone.utc).isoformat(),
        "root_cause_hypotheses": root_causes,
        "actions": unique_actions,
        "infrastructure_changes_executed": False,
        "human_review_required_before_changes": True
    }


if __name__ == "__main__":
    sample_report = {
        "detected_anomalies": [
            "memory_percent is high: 96",
            "latency_ms is high: 2800",
            "Database failures detected: 3"
        ],
        "likely_root_causes": [
            "Possible memory pressure",
            "Possible database connection bottleneck"
        ]
    }

    plan = create_remediation_plan(sample_report)

    import json
    print(json.dumps(plan, indent=2))
