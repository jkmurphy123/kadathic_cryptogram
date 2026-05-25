"""Top bar controls — provider, model, cipher selectors, and test connection."""

from time import perf_counter

from nicegui import ui

from kadathic_cryptogram.backend.client import AgentFoundryClient, FakeAgentFoundryClient
from kadathic_cryptogram.ciphers.registry import CipherRegistry
from kadathic_cryptogram.config import FrontendConfig
from kadathic_cryptogram.state.app_state import CryptogramUiState


def build_top_bar(
    *,
    config: FrontendConfig,
    state: CryptogramUiState,
    cipher_registry: CipherRegistry,
    client: AgentFoundryClient | FakeAgentFoundryClient,
) -> None:
    """Render the top bar with provider, model, and cipher dropdowns."""

    ciphers = cipher_registry.list()
    cipher_options = {cipher_type: name for cipher_type, name in ciphers}

    providers = client.list_providers()
    provider_options = {p.id: p.id for p in providers}
    model_map = {p.id: p.model or "unknown" for p in providers}

    with ui.row().classes(
        "w-full items-center gap-4 bg-white px-4 py-3 border-b"
    ):
        ui.label(config.ui.title).classes("text-lg font-semibold text-slate-900")
        ui.space()

        ui.select(
            cipher_options,
            label="Cipher",
            value=state.selected_cipher,
            on_change=lambda event: _select_cipher(state, str(event.value)),
        ).classes("w-48")

        ui.select(
            provider_options,
            label="Provider",
            value=state.selected_provider_id,
            on_change=lambda event: _select_provider(
                state, str(event.value), model_map
            ),
        ).classes("w-36")

        ui.label(
            f"Model: {state.selected_model or '—'}"
        ).classes("text-xs text-slate-500 min-w-32")

        ui.button(
            "Test Connection",
            icon="network_check",
            on_click=lambda: _test_connection(state, client, config),
        ).props("outline size=sm").classes("ml-2")


def _select_cipher(state: CryptogramUiState, cipher_type: str) -> None:
    state.selected_cipher = cipher_type
    state.ciphertext_output = ""
    state.last_key = ""
    state.plaintext_output = ""
    state.status = "ready"


def _select_provider(
    state: CryptogramUiState,
    provider_id: str,
    model_map: dict[str, str],
) -> None:
    state.selected_provider_id = provider_id
    state.selected_model = model_map.get(provider_id)


async def _test_connection(
    state: CryptogramUiState,
    client: AgentFoundryClient | FakeAgentFoundryClient,
    config: FrontendConfig,
) -> None:
    """Send a quick test prompt to verify the agent + provider are working."""

    provider = state.selected_provider_id or "unknown"
    model = state.selected_model or "unknown"
    agent_id = config.solve.agent_id

    ui.notify(
        f"Testing {agent_id} on {provider} ({model})...",
        type="info",
        position="top",
    )

    state.is_busy = True
    state.status = "testing connection..."

    try:
        started = perf_counter()
        reply = client.send_message(
            agent_id=agent_id,
            user_message="Hello! Respond with exactly: OK",
            provider_id=state.selected_provider_id,
        )
        elapsed = round((perf_counter() - started) * 1000)

        response_text = reply.text.strip()

        if len(response_text) > 0:
            state.last_latency_ms = elapsed
            state.last_provider = reply.provider_id or provider
            state.last_model = reply.model or model
            state.status = "connection OK"

            snippet = response_text[:80] + ("..." if len(response_text) > 80 else "")
            ui.notify(
                f"OK — {reply.provider_id}/{reply.model} replied in {elapsed}ms\n"
                f"Response: {snippet}",
                type="positive",
                position="top",
                timeout=8000,
            )
        else:
            state.last_error = "Empty response from provider"
            state.status = "connection failed"
            ui.notify(
                f"FAIL — {provider} returned an empty response.",
                type="negative",
                position="top",
            )

    except Exception as exc:
        state.last_error = str(exc)
        state.status = "connection failed"
        ui.notify(
            f"FAIL — {type(exc).__name__}: {exc}",
            type="negative",
            position="top",
            timeout=10000,
        )

    finally:
        state.is_busy = False
