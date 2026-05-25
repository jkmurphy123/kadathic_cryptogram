"""Mode panel — Generate / Solve toggle (left side)."""

from nicegui import ui

from kadathic_cryptogram.state.app_state import AppMode, CryptogramUiState


def build_mode_panel(*, state: CryptogramUiState) -> None:
    """Build the left-side mode toggle panel."""

    ui.label("Mode").classes("text-xs font-semibold text-slate-500 uppercase")

    with ui.column().classes("gap-2"):
        gen_btn = ui.button(
            "Generate",
            icon="lock",
            on_click=lambda: _switch_mode(state, AppMode.GENERATE),
        ).classes("w-full")
        gen_btn.props(
            f'color="primary"' if state.active_mode == AppMode.GENERATE else "flat"
        )

        sol_btn = ui.button(
            "Solve",
            icon="lock_open",
            on_click=lambda: _switch_mode(state, AppMode.SOLVE),
        ).classes("w-full")
        sol_btn.props(
            f'color="primary"' if state.active_mode == AppMode.SOLVE else "flat"
        )

        # Store buttons on state for visual update on toggle
        state._gen_btn = gen_btn
        state._solve_btn = sol_btn


def _switch_mode(state: CryptogramUiState, mode: AppMode) -> None:
    state.active_mode = mode
    state.status = "ready"
    state.last_error = None

    # Update button styling
    gen_btn = getattr(state, "_gen_btn", None)
    sol_btn = getattr(state, "_solve_btn", None)
    if gen_btn is not None:
        gen_btn.props("color=primary" if mode == AppMode.GENERATE else "flat")
    if sol_btn is not None:
        sol_btn.props("color=primary" if mode == AppMode.SOLVE else "flat")

    # Toggle panel visibility
    gen_col = getattr(state, "_gen_container", None)
    solve_col = getattr(state, "_solve_container", None)
    if gen_col is not None:
        gen_col.set_visibility(mode == AppMode.GENERATE)
    if solve_col is not None:
        solve_col.set_visibility(mode == AppMode.SOLVE)
