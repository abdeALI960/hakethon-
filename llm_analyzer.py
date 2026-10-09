"""Backward-compatible root-level incident analyzer."""

from collections.abc import Mapping
from typing import Any

from backend.services.llm.service import analyze_incident as _analyze_incident


async def analyze_incident(metrics: Mapping[str, Any], logs: list[str]) -> dict[str, Any]:
    return await _analyze_incident(metrics, logs)
