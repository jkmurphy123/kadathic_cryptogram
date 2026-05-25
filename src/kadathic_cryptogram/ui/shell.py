"""Top-level NiceGUI shell composition for the cryptogram app."""

from nicegui import ui

from kadathic_cryptogram.backend.client import AgentFoundryClient, FakeAgentFoundryClient
from kadathic_cryptogram.ciphers.registry import CipherRegistry
from kadathic_cryptogram.config import FrontendConfig
from kadathic_cryptogram.state.app_state import AppMode, CryptogramUiState
from kadathic_cryptogram.ui.generate_panel import build_generate_panel
from kadathic_cryptogram.ui.mode_panel import build_mode_panel
from kadathic_cryptogram.ui.solve_panel import build_solve_panel
from kadathic_cryptogram.ui.status_bar import build_status_bar
from kadathic_cryptogram.ui.top_bar import build_top_bar


def build_shell(
    *,
    config: FrontendConfig,
    state: CryptogramUiState,
    cipher_registry: CipherRegistry,
    client: AgentFoundryClient | FakeAgentFoundryClient,
) -> None:
    """Build the cryptogram app shell with 4-panel layout."""

    ui.page_title(config.ui.title)
    ui.add_head_html("""
        <style>
          body { margin: 0; background: #f8fafc; }
          .af-shell { max-width: 1100px; margin: 0 auto; }
          .af-cipher-output { font-family: "Courier New", monospace; font-size: 14px; }
          .af-key-display { font-family: "Courier New", monospace; font-size: 12px;
                            background: #f1f5f9; border-radius: 6px; }
        </style>
    """)

    with ui.column().classes("af-shell w-full h-screen no-wrap gap-0"):
        build_top_bar(config=config, state=state, cipher_registry=cipher_registry, client=client)

        with ui.row().classes("w-full grow gap-0"):
            with ui.column().classes("w-40 bg-white border-r p-4 gap-3"):
                build_mode_panel(state=state)

            with ui.column().classes("grow p-4 gap-3 overflow-auto"):
                gen_col = ui.column().classes("w-full gap-3")
                with gen_col:
                    build_generate_panel(
                        config=config,
                        state=state,
                        cipher_registry=cipher_registry,
                    )

                solve_col = ui.column().classes("w-full gap-3")
                with solve_col:
                    build_solve_panel(
                        config=config,
                        state=state,
                        cipher_registry=cipher_registry,
                        client=client,
                    )

                state._gen_container = gen_col
                state._solve_container = solve_col

                gen_col.set_visibility(state.active_mode == AppMode.GENERATE)
                solve_col.set_visibility(state.active_mode == AppMode.SOLVE)

        build_status_bar(state=state)
