from enum import Enum

from pydantic import BaseModel, ConfigDict, Field


class DiagnosisSeverity(str, Enum):
    CRIT = "CRIT"
    WARN = "WARN"


class RecommendedAction(str, Enum):
    RESTART = "restart"
    KILL_SPINLOOP = "kill_spinloop"
    CLEAR_LATENCY = "clear_latency"
    NONE = "none"


class LLMDiagnosis(BaseModel):
    model_config = ConfigDict(extra="forbid")

    root_cause: str = Field(min_length=1, max_length=2000)
    confidence: float = Field(ge=0, le=1)
    severity: DiagnosisSeverity
    recommended_action: RecommendedAction
    rationale: str = Field(min_length=1, max_length=2000)
    evidence: list[str] = Field(max_length=50)
