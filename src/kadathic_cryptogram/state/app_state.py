"""Local UI state for the cryptogram app."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum


class AppMode(str, Enum):
    GENERATE = "generate"
    SOLVE = "solve"


@dataclass
class CryptogramUiState:
    """Mutable state for one local cryptogram UI session."""

    # Selectors
    selected_provider_id: str | None = None
    selected_model: str | None = None
    selected_cipher: str = "substitution"

    # Mode
    active_mode: AppMode = AppMode.GENERATE

    # Generate state
    plaintext_input: str = ""
    ciphertext_output: str = ""
    last_key: str = ""

    # Solve state
    ciphertext_input: str = ""
    plaintext_output: str = ""
    solve_success: bool | None = None
    solve_attempts: int = 0
    solve_derived_key: str = ""
    solve_details: list[str] = field(default_factory=list)

    # General
    is_busy: bool = False
    status: str = "ready"
    last_error: str | None = None
    last_provider: str | None = None
    last_latency_ms: int | None = None
    max_text_length: int = 2000
    min_text_length: int = 50
