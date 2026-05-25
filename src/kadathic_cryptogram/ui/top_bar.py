"""Top bar controls — provider, model, and cipher selectors."""

from nicegui import ui

from kadathic_cryptogram.ciphers.registry import CipherRegistry
from kadathic_cryptogram.config import FrontendConfig
from kadathic_cryptogram.state.app_state import CryptogramUiState


def build_top_bar(
    *,
    config: FrontendConfig,
    state: CryptogramUiState,
    cipher_registry: CipherRegistry,
) -> None:
    """Render the top bar with provider, model, and cipher dropdowns."""

    ciphers = cipher_registry.list()
    cipher_options = {cipher_type: name for cipher_type, name in ciphers}

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

        ui.label("| Provider / Model — Milestone 2").classes(
            "text-xs text-slate-400 italic"
        )


def _select_cipher(state: CryptogramUiState, cipher_type: str) -> None:
    state.selected_cipher = cipher_type
    # Clear outputs when switching cipher
    state.ciphertext_output = ""
    state.last_key = ""
    state.plaintext_output = ""
    state.status = "ready"
