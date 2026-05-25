"""UI-safe models returned by backend client adapters."""

from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any


@dataclass(frozen=True)
class ProviderSummary:
    """Small provider summary for selectors and status displays."""

    id: str
    type: str
    model: str | None = None


@dataclass(frozen=True)
class ChatReply:
    """LLM response plus backend metadata useful to the UI."""

    text: str
    agent_id: str
    session_id: str
    provider_id: str | None = None
    model: str | None = None
    context_capsule_id: str | None = None
    latency_ms: int | None = None
    metadata: dict[str, Any] = field(default_factory=dict)
