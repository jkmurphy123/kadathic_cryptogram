"""Generate panel — plaintext input + generate button + ciphertext output."""

from nicegui import ui

from kadathic_cryptogram.ciphers.registry import CipherRegistry
from kadathic_cryptogram.config import FrontendConfig
from kadathic_cryptogram.state.app_state import CryptogramUiState


def build_generate_panel(
    *,
    config: FrontendConfig,
    state: CryptogramUiState,
    cipher_registry: CipherRegistry,
) -> None:
    """Build the Generate mode panel (right side)."""

    ui.label("Generate Cipher").classes("text-base font-semibold text-slate-800")

    # Plaintext input
    plaintext_area = ui.textarea(
        label="Enter your message",
        placeholder="Type or paste the text you want to encrypt...",
        value=state.plaintext_input,
        on_change=lambda e: _update_plaintext(state, str(e.value or "")),
    ).classes("w-full")
    plaintext_area.props("rows=6 outlined")

    # Character count
    char_label = ui.label("0 characters").classes("text-xs text-slate-500")

    # Length warning
    length_warning = ui.label("").classes("text-xs text-amber-600 invisible")

    # Generate button
    gen_btn = ui.button(
        "Generate",
        icon="vpn_key",
        on_click=lambda: _do_generate(
            state, cipher_registry, length_warning
        ),
    ).classes("mt-2")

    # Ciphertext output (read-only)
    ui.label("Ciphertext").classes("text-sm font-medium text-slate-700 mt-4")
    ciphertext_area = ui.textarea(
        label="Encrypted text",
        value=state.ciphertext_output,
    ).classes("w-full af-cipher-output")
    ciphertext_area.props("rows=6 outlined readonly")

    # Key display
    key_label = ui.label("").classes(
        "af-key-display w-full p-3 text-xs break-all select-all"
    )

    # Store shared UI elements on state for updates
    state._gen_plaintext_area = plaintext_area
    state._gen_char_label = char_label
    state._gen_length_warning = length_warning
    state._gen_ciphertext_area = ciphertext_area
    state._gen_key_label = key_label
    state._gen_button = gen_btn


def _update_plaintext(state: CryptogramUiState, text: str) -> None:
    state.plaintext_input = text
    char_label = getattr(state, "_gen_char_label", None)
    length_warning = getattr(state, "_gen_length_warning", None)
    if char_label is not None:
        char_label.set_text(f"{len(text)} characters")
    if length_warning is not None:
        if len(text) < state.min_text_length:
            length_warning.set_text(
                f"Text is short ({len(text)} chars). "
                f"Minimum {state.min_text_length} recommended for good ciphers."
            )
            length_warning.classes("text-xs text-amber-600", remove="invisible")
        elif len(text) > state.max_text_length:
            length_warning.set_text(
                f"Text exceeds {state.max_text_length} chars. It will be truncated."
            )
            length_warning.classes("text-xs text-red-600", remove="invisible")
        else:
            length_warning.classes("text-xs text-amber-600 invisible")


def _do_generate(
    state: CryptogramUiState,
    cipher_registry: CipherRegistry,
    length_warning: ui.label,
) -> None:
    """Generate ciphertext from plaintext input."""
    text = state.plaintext_input.strip()
    if not text:
        ui.notify("Please enter some text to encrypt.", type="warning")
        return

    # Truncate if too long
    if len(text) > state.max_text_length:
        text = text[: state.max_text_length]
        state.plaintext_input = text

    try:
        cipher = cipher_registry.get(state.selected_cipher)
        key = cipher.generate_key()
        ciphertext = cipher.encrypt(text, key)

        state.ciphertext_output = ciphertext
        state.last_key = key
        state.status = "generated"

        # Update UI
        cta = getattr(state, "_gen_ciphertext_area", None)
        kl = getattr(state, "_gen_key_label", None)
        if cta is not None:
            cta.set_value(ciphertext)
        if kl is not None:
            kl.set_text(f"Key: {key}")

    except Exception as exc:
        state.last_error = str(exc)
        state.status = "error"
        ui.notify(f"Generation failed: {exc}", type="negative")
