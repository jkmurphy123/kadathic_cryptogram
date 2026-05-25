"""NiceGUI app factory for the cryptogram shell."""

from kadathic_cryptogram.backend.client import AgentFoundryClient, FakeAgentFoundryClient
from kadathic_cryptogram.ciphers.registry import create_default_registry
from kadathic_cryptogram.config import FrontendConfig, load_frontend_config
from kadathic_cryptogram.state.app_state import CryptogramUiState


def create_app(
    config: FrontendConfig | None = None,
    *,
    backend_client: AgentFoundryClient | FakeAgentFoundryClient | None = None,
) -> CryptogramUiState:
    """Create the NiceGUI page and return the initial UI state."""

    from kadathic_cryptogram.ui.shell import build_shell

    active_config = config or load_frontend_config()
    cipher_registry = create_default_registry()
    client = backend_client or _create_backend_client(active_config)
    state = _create_initial_state(active_config, client)

    build_shell(
        config=active_config,
        state=state,
        cipher_registry=cipher_registry,
        client=client,
    )
    return state


def _create_backend_client(
    config: FrontendConfig,
) -> AgentFoundryClient | FakeAgentFoundryClient:
    try:
        return AgentFoundryClient(config.backend.project_config_path)
    except Exception:
        fallback = FakeAgentFoundryClient(
            project_id=config.backend.project_id,
        )
        return fallback


def _create_initial_state(
    config: FrontendConfig,
    client: AgentFoundryClient | FakeAgentFoundryClient,
) -> CryptogramUiState:
    state = CryptogramUiState(
        selected_provider_id=config.ui.default_provider_id,
        selected_cipher=config.ui.default_cipher,
        max_text_length=config.solve.max_ciphertext_length,
        min_text_length=config.solve.min_ciphertext_length,
    )

    try:
        providers = client.list_providers()
        if providers:
            if config.ui.default_provider_id is None:
                state.selected_provider_id = providers[0].id
                state.selected_model = providers[0].model
            else:
                # Look up model for the configured provider
                for p in providers:
                    if p.id == state.selected_provider_id:
                        state.selected_model = p.model
                        break
    except Exception:
        pass

    return state
