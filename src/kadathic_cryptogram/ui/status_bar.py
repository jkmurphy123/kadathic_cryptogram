"""Status bar for the cryptogram app."""

from nicegui import ui

from kadathic_cryptogram.state.app_state import CryptogramUiState


def build_status_bar(*, state: CryptogramUiState) -> None:
    """Render compact session and status details."""

    cipher_text = state.selected_cipher or "none"
    provider_text = state.selected_provider_id or state.last_provider or "—"
    latency_text = (
        f"{state.last_latency_ms} ms"
        if state.last_latency_ms is not None
        else "—"
    )

    with ui.row().classes(
        "w-full items-center gap-4 bg-white px-4 py-2 border-t text-xs text-slate-600"
    ):
        ui.label(f"Status: {state.status}")
        ui.label(f"Cipher: {cipher_text}")
        ui.label(f"Provider: {provider_text}")
        ui.label(f"Model: {state.selected_model or '—'}")
        ui.label(f"Latency: {latency_text}")
        if state.last_error:
            ui.label(f"Error: {state.last_error}").classes("text-red-700")
