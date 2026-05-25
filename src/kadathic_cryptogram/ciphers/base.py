"""Cipher protocol and result types."""

from dataclasses import dataclass, field
from typing import Protocol


@dataclass(frozen=True)
class CipherResult:
    """Result of encrypting plaintext with a cipher."""

    plaintext: str
    ciphertext: str
    key: str  # human-readable, e.g. "A→Q B→Z C→E ..."
    cipher_type: str  # e.g. "substitution"


@dataclass
class SolveResult:
    """Result of an AI solve attempt."""

    plaintext: str
    success: bool
    attempts: int
    total_latency_ms: int
    derived_key: str = ""
    validation_details: list[str] = field(default_factory=list)


class CipherProtocol(Protocol):
    """Contract every cipher type must satisfy."""

    cipher_type: str

    def generate_key(self) -> str:
        """Return a random key string for this cipher."""
        ...

    def encrypt(self, plaintext: str, key: str) -> str:
        """Encrypt plaintext using the given key."""
        ...

    def decrypt(self, ciphertext: str, key: str) -> str:
        """Decrypt ciphertext using the given key (deterministic)."""
        ...

    def solve_prompt(self, ciphertext: str) -> str:
        """Return the full prompt to send to the LLM for cracking."""
        ...

    def validate_solution(self, ciphertext: str, claimed_plaintext: str) -> bool:
        """Check if claimed plaintext is a valid decryption of the ciphertext."""
        ...

    def retry_prompt(self, ciphertext: str, failed_guess: str) -> str:
        """Return a stronger follow-up prompt when first attempt fails."""
        ...

    def derive_key(self, ciphertext: str, plaintext: str) -> str:
        """Derive the key mapping from ciphertext→plaintext (for display)."""
        ...
