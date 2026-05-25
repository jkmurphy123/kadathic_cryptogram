"""Solve panel — ciphertext input + solve button + plaintext output.

Wired to the SolverEngine for AI-powered cipher cracking.
"""

from nicegui import ui

from kadathic_cryptogram.backend.client import AgentFoundryClient, FakeAgentFoundryClient
from kadathic_cryptogram.ciphers.registry import CipherRegistry
from kadathic_cryptogram.config import FrontendConfig
from kadathic_cryptogram.solver.engine import SolverEngine
from kadathic_cryptogram.state.app_state import CryptogramUiState


def build_solve_panel(
    *,
    config: FrontendConfig,
    state: CryptogramUiState,
    cipher_registry: CipherRegistry,
    client: AgentFoundryClient | FakeAgentFoundryClient,
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
        on_click=lambda: _do_solve(
            state, cipher_registry, client, config, length_warning
        ),
    ).classes("mt-2")

    # Progress / attempts display
    progress_label = ui.label("").classes("text-sm text-blue-700 mt-1")

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

    # Success/failure badge
    result_badge = ui.label("").classes("text-sm font-semibold mt-1")

    # Store shared UI elements on state for updates
    state._solve_ciphertext_area = ciphertext_area
    state._solve_char_label = char_label
    state._solve_length_warning = length_warning
    state._solve_button = solve_btn
    state._solve_progress_label = progress_label
    state._solve_plaintext_area = plaintext_area
    state._solve_derived_key_label = derived_key_label
    state._solve_result_badge = result_badge


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


async def _do_solve(
    state: CryptogramUiState,
    cipher_registry: CipherRegistry,
    client: AgentFoundryClient | FakeAgentFoundryClient,
    config: FrontendConfig,
    length_warning: ui.label,
) -> None:
    """Run the AI-powered solver with retry logic."""

    text = state.ciphertext_input.strip()
    if not text:
        ui.notify("Please enter ciphertext to solve.", type="warning")
        return

    if len(text) > state.max_text_length:
        text = text[: state.max_text_length]
        state.ciphertext_input = text

    # Disable button, show spinner
    solve_btn = getattr(state, "_solve_button", None)
    progress_label = getattr(state, "_solve_progress_label", None)

    state.is_busy = True
    state.status = "solving..."
    state.last_error = None

    if solve_btn is not None:
        solve_btn.set_enabled(False)

    if progress_label is not None:
        progress_label.set_text("Solving... (this may take a moment)")

    try:
        engine = SolverEngine(
            client=client,
            cipher_registry=cipher_registry,
            agent_id=config.solve.agent_id,
            max_retries=config.solve.max_retries,
            log_enabled=config.solve.log_enabled,
        )

        result = engine.solve(
            text,
            state.selected_cipher,
            provider_id=state.selected_provider_id,
        )

        state.plaintext_output = result.plaintext
        state.solve_success = result.success
        state.solve_attempts = result.attempts
        state.solve_derived_key = result.derived_key
        state.solve_details = result.validation_details
        state.last_latency_ms = result.total_latency_ms
        state.last_provider = state.selected_provider_id or "mock"

        # Update UI
        plaintext_area = getattr(state, "_solve_plaintext_area", None)
        derived_key_label = getattr(state, "_solve_derived_key_label", None)
        result_badge = getattr(state, "_solve_result_badge", None)

        if plaintext_area is not None:
            plaintext_area.set_value(result.plaintext)

        if derived_key_label is not None:
            if result.derived_key:
                derived_key_label.set_text(f"Derived Key: {result.derived_key}")
            else:
                derived_key_label.set_text("")

        if result_badge is not None:
            if result.success:
                result_badge.set_text(
                    f"Solved in {result.attempts} attempt(s) "
                    f"({result.total_latency_ms}ms)"
                )
                result_badge.classes("text-sm font-semibold text-green-700 mt-1")
            else:
                result_badge.set_text(
                    f"Failed after {result.attempts} attempt(s)"
                )
                result_badge.classes("text-sm font-semibold text-red-700 mt-1")

        if progress_label is not None:
            details = "\n".join(result.validation_details)
            progress_label.set_text(details)

        state.status = "solved" if result.success else "solve failed"

        if result.success:
            ui.notify(
                f"Solved in {result.attempts} attempt(s)!",
                type="positive",
            )
        else:
            ui.notify(
                f"Could not crack after {result.attempts} attempts.",
                type="warning",
            )

    except Exception as exc:
        state.last_error = str(exc)
        state.status = "error"
        state.plaintext_output = f"Error: {exc}"
        plaintext_area = getattr(state, "_solve_plaintext_area", None)
        if plaintext_area is not None:
            plaintext_area.set_value(f"Error: {exc}")
        ui.notify(f"Solve failed: {exc}", type="negative")

    finally:
        state.is_busy = False
        if solve_btn is not None:
            solve_btn.set_enabled(True)
