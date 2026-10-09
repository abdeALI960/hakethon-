
def detect_anomalies(metrics: dict) -> list[str]:
    """Detect cloud reliability problems from numeric metrics."""

    alerts = []

    thresholds = {
        "cpu_percent": 85,
        "memory_percent": 90,
        "latency_ms": 2000,
        "error_rate_percent": 5,
    }

    for metric, threshold in thresholds.items():
        if metric not in metrics:
            continue

        value = metrics[metric]

        if not isinstance(value, (int, float)) or isinstance(value, bool):
            alerts.append(f"Invalid metric: {metric}")
            continue

        if metric in ("cpu_percent", "memory_percent", "error_rate_percent"):
            if not 0 <= value <= 100:
                alerts.append(f"Invalid metric: {metric}")
                continue
        elif value < 0:
            alerts.append(f"Invalid metric: {metric}")
            continue

        if value >= threshold:
            alerts.append(
                f"{metric} is high: {value} (threshold: {threshold})"
            )

    db_failures = metrics.get("database_failures", 0)

    if (
        not isinstance(db_failures, (int, float))
        or isinstance(db_failures, bool)
        or db_failures < 0
    ):
        alerts.append("Invalid metric: database_failures")
    elif db_failures > 0:
        alerts.append(f"Database failures detected: {db_failures}")

    return alerts


if __name__ == "__main__":
    sample_metrics = {
        "cpu_percent": 35,
        "memory_percent": 96,
        "latency_ms": 2800,
        "error_rate_percent": 8,
        "database_failures": 3,
    }

    for alert in detect_anomalies(sample_metrics):
        print("-", alert)
