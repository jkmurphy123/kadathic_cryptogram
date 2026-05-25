"""Backend client adapters for Agent Foundry."""

from __future__ import annotations

from collections.abc import Iterable
from pathlib import Path
from secrets import token_hex
from time import perf_counter

from kadathic_cryptogram.backend.models import ChatReply, ProviderSummary

CRYPTOGRAM_CONTEXT_SUMMARY = (
    "Cryptogram solver session. The user is providing ciphertext encrypted with "
    "a simple substitution cipher. Decrypt it and return only the plaintext."
)


class AgentFoundryClient:
    """Thin adapter around the Agent Foundry backend runtime."""

    def __init__(self, project_config_path: str | Path) -> None:
        from agent_foundry import AgentRuntime

        self.project_config_path = Path(project_config_path)
        self.runtime = AgentRuntime.from_project_config(self.project_config_path)

    @property
    def project_id(self) -> str:
        return self.runtime.project_config.project.id

    def list_providers(self) -> list[ProviderSummary]:
        summaries: list[ProviderSummary] = []
        for provider_id, provider_config in sorted(
            self.runtime.project_config.providers.items()
        ):
            summaries.append(
                ProviderSummary(
                    id=provider_id,
                    type=provider_config.type,
                    model=provider_config.model,
                )
            )
        return summaries

    def send_message(
        self,
        *,
        agent_id: str,
        user_message: str,
        provider_id: str | None = None,
    ) -> ChatReply:
        """Send one stateless message through the backend runtime."""

        from agent_foundry import AppContext

        started = perf_counter()
        response = self.runtime.chat(
            agent_id=agent_id,
            project_id=self.project_id,
            session_id=_generate_session_id(),
            user_id="local-user",
            user_message=user_message,
            app_context=AppContext.simple(
                app_id="kadathic_cryptogram",
                app_type="cryptogram",
                title="Kadathic Cryptogram Solver",
                state_summary=CRYPTOGRAM_CONTEXT_SUMMARY,
            ),
        )
        latency_ms = round((perf_counter() - started) * 1000)
        metadata = dict(response.metadata)
        if provider_id is not None:
            metadata["requested_provider_id"] = provider_id
        return ChatReply(
            text=response.text,
            agent_id=response.agent_id,
            session_id=response.session_id,
            provider_id=response.provider_id,
            model=response.model,
            context_capsule_id=response.context_capsule_id,
            latency_ms=latency_ms,
            metadata=metadata,
        )


class FakeAgentFoundryClient:
    """Deterministic backend client for frontend development and tests."""

    def __init__(
        self,
        *,
        providers: Iterable[ProviderSummary] | None = None,
        project_id: str = "cryptogram_project",
    ) -> None:
        self._providers = list(providers) if providers is not None else [
            ProviderSummary("mock", "mock", "mock-model"),
        ]
        self.project_id = project_id
        self.sent_messages: list[tuple[str, str]] = []

    def list_providers(self) -> list[ProviderSummary]:
        return list(self._providers)

    def send_message(
        self,
        *,
        agent_id: str,
        user_message: str,
        provider_id: str | None = None,
    ) -> ChatReply:
        self.sent_messages.append((agent_id, user_message))
        selected_provider = (
            provider_id or (self._providers[0].id if self._providers else None)
        )
        selected_model = self._providers[0].model if self._providers else None
        return ChatReply(
            text=f"fake reply from {agent_id}: {user_message[:50]}...",
            agent_id=agent_id,
            session_id=_generate_session_id(),
            provider_id=selected_provider,
            model=selected_model,
            context_capsule_id="fake-capsule",
            latency_ms=1,
            metadata={"project_id": self.project_id},
        )


def _generate_session_id() -> str:
    from datetime import UTC, datetime

    timestamp = datetime.now(UTC).strftime("%Y%m%d-%H%M%S")
    return f"cryptogram-{timestamp}-{token_hex(3)}"
