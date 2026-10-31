from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class SecurityEvent(BaseModel):
    """Normalized event. `raw` retains the source record for traceability."""

    model_config = ConfigDict(extra="allow")

    event_id: str = Field(min_length=1, max_length=200)
    source: str = Field(min_length=1, max_length=100)
    timestamp: datetime
    event_type: str = Field(min_length=1, max_length=200)
    actor: str | None = None
    action: str | None = None
    outcome: str | None = None
    ip_address: str | None = None
    resource: str | None = None
    details: dict[str, Any] = Field(default_factory=dict)
    raw: dict[str, Any] = Field(default_factory=dict)


class InvestigationRequest(BaseModel):
    question: str = Field(min_length=5, max_length=4000)
    alert_id: str | None = Field(default=None, max_length=200)
    time_window_hours: int = Field(default=72, ge=1, le=720)


class IngestEventRequest(SecurityEvent):
    pass
