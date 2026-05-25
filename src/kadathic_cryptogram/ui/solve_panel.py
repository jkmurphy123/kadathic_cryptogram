"""Solve panel — ciphertext input + solve button + plaintext output.

Milestone 1: placeholder UI only. Milestone 2: wired to AI solver.
"""

from nicegui import ui

from kadathic_cryptogram.ciphers.registry import CipherRegistry
from kadathic_cryptogram.config import FrontendConfig
from kadathic_cryptogram.state.app_state import CryptogramUiState


def build_solve_panel(
    *,
    config: FrontendConfig,
    state: CryptogramUiState,
    cipher_registry: CipherRegistry,
) -> None:
    """Build the Solve mode panel (right side)."""

    ui.label("Solve Cipher").classes("text-base font-semibold text-slate-800")

    # Ciphertext input
    ciphertext_area = ui.textarea(
        label="Enter ciphertext",
        placeholder="Paste the encrypted text you want to crack...",
        value=state.ciphertext_input,
        on_change=lambda e: _update_ciphertext(state, str(e.value or "")),
    ).classes("w-full af-cipher-output")
    ciphertext_area.props("rows=6 outlined")

    # Character count
    char_label = ui.label("0 characters").classes("text-xs text-slate-500")

    # Length warning
    length_warning = ui.label("").classes("text-xs text-amber-600 invisible")

    # Solve button
    solve_btn = ui.button(
        "Solve",
        icon="psychology",
        on_click=lambda: _do_solve_placeholder(state, length_warning),
    ).classes("mt-2")

    # Plaintext output
    ui.label("Decrypted Text").classes("text-sm font-medium text-slate-700 mt-4")
    plaintext_area = ui.textarea(
        label="Decrypted plaintext",
        value=state.plaintext_output,
    ).classes("w-full")
    plaintext_area.props("rows=6 outlined readonly")

    # Derived key (shown on successful solve)
    derived_key_label = ui.label("").classes(
        "af-key-display w-full p-3 text-xs break-all select-all mt-2"
    )

    # Attempts info
    attempts_label = ui.label("").classes("text-xs text-slate-500 mt-1")

    # Store shared UI elements on state for updates
    state._solve_ciphertext_area = ciphertext_area
    state._solve_char_label = char_label
    state._solve_length_warning = length_warning
    state._solve_button = solve_btn
    state._solve_plaintext_area = plaintext_area
    state._solve_derived_key_label = derived_key_label
    state._solve_attempts_label = attempts_label


def _update_ciphertext(state: CryptogramUiState, text: str) -> None:
    state.ciphertext_input = text
    char_label = getattr(state, "_solve_char_label", None)
    length_warning = getattr(state, "_solve_length_warning", None)
    if char_label is not None:
        char_label.set_text(f"{len(text)} characters")
    if length_warning is not None:
        if len(text) < state.min_text_length:
            length_warning.set_text(
                f"Text is very short ({len(text)} chars). "
                f"At least {state.min_text_length} chars needed for reliable solve."
            )
            length_warning.classes("text-xs text-amber-600", remove="invisible")
        elif len(text) > state.max_text_length:
            length_warning.set_text(
                f"Text exceeds {state.max_text_length} chars. It will be truncated."
            )
            length_warning.classes("text-xs text-red-600", remove="invisible")
        else:
            length_warning.classes("text-xs text-amber-600 invisible")


def _do_solve_placeholder(
    state: CryptogramUiState,
    length_warning: ui.label,
) -> None:
    """Placeholder — real AI solver comes in Milestone 2."""
    text = state.ciphertext_input.strip()
    if not text:
        ui.notify("Please enter ciphertext to solve.", type="warning")
        return

    ui.notify(
        "AI-powered solving will be available in Milestone 2.",
        type="info",
    )
    state.status = "solve not implemented yet"
