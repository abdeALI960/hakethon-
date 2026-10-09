from enum import Enum
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator
from pydantic.alias_generators import to_camel


class CamelModel(BaseModel):
    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
        str_max_length=10_000,
    )


class ChaosType(str, Enum):
    CRASH = "CRASH"
    CPU_SPIKE = "CPU_SPIKE"
    HIGH_LATENCY = "HIGH_LATENCY"
    OOM_KILL = "OOM_KILL"


class RemediationRequestAction(str, Enum):
    RESTART = "restart"
    KILL_SPINLOOP = "kill_spinloop"
    CLEAR_LATENCY = "clear_latency"
    UI_RESTART = "python fixer.py restart api"
    UI_KILL_SPINLOOP = 'kill -SIGUSR1 $(pgrep -f "worker/spinloop")'
    UI_CLEAR_LATENCY = "curl -X POST http://127.0.0.1:5001/admin/reset-delay"


class ChaosInjectionRequest(CamelModel):
    service: Literal["web", "api", "worker"]
    port: int
    type: ChaosType


class ChaosInjectionResponse(CamelModel):
    status: Literal["injected"]
    command: str
    target_pid: int | None


class RemediationRequest(CamelModel):
    service: Literal["web", "api", "worker"]
    action: RemediationRequestAction


class RemediationResponse(CamelModel):
    status: Literal["recovered", "failed"]
    new_pid: int | None
    probe_verified: bool
    fix_duration_sec: float


class ProbeResponse(CamelModel):
    http_status: int | None
    ping_latency_ms: float
    ssl_cert_days: int | None
    last_checked_utc: str


class HealthResponse(CamelModel):
    status: Literal["ok"]
    service: Literal["OpsPilot"]


class EmergencyIntakeRequest(CamelModel):
    incident_type: str = Field(min_length=1, max_length=200)
    location: str = Field(min_length=1, max_length=300)
    priority: Literal["RED", "YELLOW", "GREEN"]
    reported_by: str = Field(min_length=1, max_length=120)
    description: str = Field(min_length=1, max_length=2000)

    @field_validator(
        "incident_type",
        "location",
        "reported_by",
        "description",
        mode="before",
    )
    @classmethod
    def trim_text(cls, value: object) -> object:
        return value.strip() if isinstance(value, str) else value


class EmergencyIntakeResponse(CamelModel):
    case_id: str
    status: Literal["Dispatched"]
    ai_triage_summary: str
    safety_notice: Literal[
        "AI output is decision support only and does not replace professional human evaluation."
    ] = "AI output is decision support only and does not replace professional human evaluation."


class EmergencyEvidenceUploadResponse(CamelModel):
    case_id: str
    status: Literal["uploaded"]
    content_type: Literal["image/png", "image/jpeg", "image/webp"]


class ServiceHealth(CamelModel):
    service: str
    port: int | None
    status: Literal["healthy", "degraded", "critical", "recovering"]
    latency_ms: float | None
    last_checked_utc: str | None


class IncidentLogResponse(CamelModel):
    ts: str
    level: str
    message: str


class IncidentResponse(CamelModel):
    id: str
    service: str
    port: int | None
    anomaly_type: str
    severity: Literal["CRITICAL", "HIGH", "MEDIUM", "LOW"]
    auto_healed: bool
    status: str
    injected_at: str | None
    detected_at: str | None
    diagnosed_at: str | None
    fixed_at: str | None
    verified_at: str | None
    detection_duration_sec: float | None
    fix_duration_sec: float | None
    ai_rationale: str | None
    logs: list[IncidentLogResponse]


class IncidentListResponse(CamelModel):
    incidents: list[IncidentResponse]
    total: int
    limit: int
    offset: int


class DurationStats(CamelModel):
    avg: float | None
    std_dev: float | None = None


class MttrStats(CamelModel):
    avg: float | None


class KpiResponse(CamelModel):
    total_incidents: int
    auto_healed_rate_percent: float
    human_escalations: int
    mttd_seconds: DurationStats
    mttr_seconds: MttrStats


class EndpointResponse(CamelModel):
    id: int
    name: str
    url: str
    service_key: str | None
    port: int | None
    probe_interval_seconds: float
    enabled: bool
    is_demo_target: bool
    created_at: str


class EndpointListResponse(CamelModel):
    endpoints: list[EndpointResponse]


class EndpointCreateRequest(CamelModel):
    name: str = Field(min_length=1, max_length=80)
    url: str = Field(min_length=1, max_length=1000)
    service_key: str | None = Field(default=None, max_length=32)
    port: int | None = Field(default=None, ge=1, le=65535)
    probe_interval_seconds: ProbeIntervalInput = 2.0
    enabled: bool = True


class EndpointPatchRequest(CamelModel):
    probe_interval_seconds: ProbeIntervalInput | None = None
    enabled: bool | None = None


class EndpointDeleteResponse(CamelModel):
    deleted: bool


class SettingsResponse(CamelModel):
    llm_provider: Literal["openai", "anthropic", "gemini"]
    p99_latency_sla_ms: float
    webhook_url: str | None
    zero_touch_enabled: bool
    operator_name: str


class SettingsUpdateRequest(CamelModel):
    llm_provider: Literal["openai", "anthropic", "gemini"] | None = None
    p99_latency_sla_ms: float | None = Field(default=None, gt=0, le=600000)
    webhook_url: str | None = Field(default=None, max_length=1000)
    zero_touch_enabled: bool | None = None
    operator_name: str | None = Field(default=None, min_length=1, max_length=120)


class AnalyzeIncidentRequest(CamelModel):
    metrics: dict[str, Any] = Field(default_factory=dict)
    logs: list[str] = Field(default_factory=list, max_length=500)


class AnalysisReport(CamelModel):
    summary: str
    root_cause: str
    confidence: float | None = None
    severity: str
    recommended_action: Literal["restart", "kill_spinloop", "clear_latency", "none"]
    rationale: str
    evidence: list[str] = Field(default_factory=list)
    llm_status: str
    latency_ms: float


class AnalyzeIncidentResponse(AnalysisReport):
    incident_id: str


class StreamEvent(CamelModel):
    type: Literal["stage_changed", "log_line", "probe_result", "incident_created"]
    incident_id: str | None = None
    endpoint_id: int | None = None
    timestamp: str
    payload: dict[str, Any] = Field(default_factory=dict)


class ErrorField(CamelModel):
    field: str
    message: str
    type: str


class ErrorBody(CamelModel):
    code: str
    message: str
    details: list[ErrorField] | None = None


class ErrorResponse(CamelModel):
    error: ErrorBody


class DbTableInfo(CamelModel):
    name: str
    row_count: int


class DbTablesResponse(CamelModel):
    tables: list[DbTableInfo]


class DbTableRowsResponse(CamelModel):
    table: str
    rows: list[dict[str, Any]]
    total: int
    limit: int
    offset: int
    q: str | None


class DbTableSchema(CamelModel):
    name: str
    create_sql: str


class DbSchemaResponse(CamelModel):
    tables: list[DbTableSchema]


class DbExportResponse(CamelModel):
    tables: dict[str, list[dict[str, Any]]]
    row_count: int
    row_cap: int
    truncated: bool


ProbeInterval = Literal["1s", "2s", "5s"]
ProbeIntervalInput = Literal[1.0, 2.0, 5.0, "1s", "2s", "5s"]


def seconds_for_probe_interval(value: ProbeInterval) -> float:
    return float(value[:-1])
