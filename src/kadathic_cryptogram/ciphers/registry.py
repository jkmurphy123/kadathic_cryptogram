"""Cipher registry — pluggable cipher types for the UI dropdown."""

from __future__ import annotations

from kadathic_cryptogram.ciphers.base import CipherProtocol
from kadathic_cryptogram.ciphers.substitution import SubstitutionCipher


class CipherRegistry:
    """Registry of available cipher types, keyed by cipher_type string."""

    def __init__(self) -> None:
        self._ciphers: dict[str, CipherProtocol] = {}

    def register(self, cipher: CipherProtocol) -> None:
        """Register a cipher implementation."""
        self._ciphers[cipher.cipher_type] = cipher

    def get(self, cipher_type: str) -> CipherProtocol:
        """Get a cipher by type string."""
        if cipher_type not in self._ciphers:
            available = ", ".join(sorted(self._ciphers))
            raise KeyError(
                f"Unknown cipher type '{cipher_type}'. Available: {available}"
            )
        return self._ciphers[cipher_type]

    def list(self) -> list[tuple[str, str]]:
        """Return (cipher_type, display_name) pairs for UI dropdowns."""
        return sorted(
            (c.cipher_type, getattr(c, "display_name", c.cipher_type))
            for c in self._ciphers.values()
        )

    def __contains__(self, cipher_type: str) -> bool:
        return cipher_type in self._ciphers


def create_default_registry() -> CipherRegistry:
    """Create a registry pre-loaded with built-in ciphers."""
    registry = CipherRegistry()
    registry.register(SubstitutionCipher())
    return registry
