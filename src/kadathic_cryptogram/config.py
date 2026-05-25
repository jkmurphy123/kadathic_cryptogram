"""Frontend configuration models and loading helpers."""

from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel, Field


class BackendConfig(BaseModel):
    """Settings used to construct the Agent Foundry backend client."""

    project_config_path: str = "./agentfoundry.yaml"
    project_id: str = "cryptogram_project"
    default_user_id: str = "local-user"


class UiConfig(BaseModel):
    """Settings that affect frontend behavior and defaults."""

    title: str = "Kadathic Cryptogram"
    default_provider_id: str | None = None
    default_cipher: str = "substitution"


class SolveConfig(BaseModel):
    """Solver engine configuration."""

    agent_id: str = "cryptogram_solver"
    max_retries: int = Field(default=3, ge=1, le=5)
    max_ciphertext_length: int = Field(default=2000, ge=50)
    min_ciphertext_length: int = Field(default=50, ge=10)
    log_enabled: bool = False


class FrontendConfig(BaseModel):
    """Top-level frontend configuration."""

    backend: BackendConfig = Field(default_factory=BackendConfig)
    ui: UiConfig = Field(default_factory=UiConfig)
    solve: SolveConfig = Field(default_factory=SolveConfig)
    source_path: Path | None = None


def load_frontend_config(
    path: str | Path | None = None,
    *,
    backend_config_path: str | Path | None = None,
) -> FrontendConfig:
    """Load frontend config from YAML, falling back to defaults."""

    config_path = _resolve_config_path(path)
    raw: dict[str, Any] = {}
    if config_path is not None:
        with config_path.open("r", encoding="utf-8") as handle:
            loaded = yaml.safe_load(handle) or {}
        if not isinstance(loaded, dict):
            raise ValueError(f"Frontend config must be a mapping: {config_path}")
        raw = loaded

    config = FrontendConfig.model_validate(raw)
    config.source_path = config_path
    if backend_config_path is not None:
        config.backend.project_config_path = str(backend_config_path)
    return config


def _resolve_config_path(path: str | Path | None) -> Path | None:
    if path is not None:
        resolved = Path(path).expanduser().resolve()
        return resolved if resolved.exists() else None

    default_path = Path("frontend.yaml")
    if default_path.exists():
        return default_path.resolve()
    return None
