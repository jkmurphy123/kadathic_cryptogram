"""Top bar controls — provider, model, and cipher selectors."""

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

    # Build model map
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
