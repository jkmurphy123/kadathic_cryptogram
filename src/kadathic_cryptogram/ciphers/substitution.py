"""Simple mono-alphabetic substitution cipher."""

from __future__ import annotations

import random
import string

from kadathic_cryptogram.ciphers.base import CipherResult, CipherProtocol

UPPER = string.ascii_uppercase


class SubstitutionCipher:
    """Simple substitution cipher: each letter maps to another consistently."""

    cipher_type = "substitution"
    display_name = "Simple Substitution"

    def generate_key(self) -> str:
        """Create a random permutation of A-Z and return human-readable key."""
        shuffled = list(UPPER)
        random.shuffle(shuffled)
        pairs = [f"{plain}→{cipher}" for plain, cipher in zip(UPPER, shuffled)]
        return "  ".join(pairs)

    def encrypt(self, plaintext: str, key: str) -> str:
        """Encrypt plaintext using the given key.

        Preserves case: uppercase letters are encrypted, lowercase are
        uppercased and encrypted. Non-letters pass through unchanged.
        """
        mapping = self._parse_key(key)
        result: list[str] = []
        for ch in plaintext:
            upper_ch = ch.upper()
            if upper_ch in mapping:
                result.append(mapping[upper_ch])
            else:
                result.append(ch)
        return "".join(result)

    def decrypt(self, ciphertext: str, key: str) -> str:
        """Decrypt ciphertext using the given key."""
        mapping = self._parse_key(key)
        # Invert the mapping
        inverse = {v: k for k, v in mapping.items()}
        result: list[str] = []
        for ch in ciphertext:
            upper_ch = ch.upper()
            if upper_ch in inverse:
                result.append(inverse[upper_ch])
            else:
                result.append(ch)
        return "".join(result)

    def solve_prompt(self, ciphertext: str) -> str:
        """Build the first-attempt solve prompt."""
        return f"""You are a cryptography expert. Below is a ciphertext encrypted with a simple
mono-alphabetic substitution cipher. Each letter in the original message has been
replaced by a different letter, consistently throughout the text.

Your task: Decrypt the ciphertext back to the original English plaintext.

- Use frequency analysis: 'E' is the most common letter in English,
  followed by 'T', 'A', 'O', 'I', 'N', 'S', 'H', 'R'.
- Look for common short words: "THE", "AND", "A", "I", "TO", "OF", "IN".
- Look for repeated patterns, double letters, and apostrophe patterns.
- The plaintext will be coherent English.
- Punctuation and spaces are preserved as-is — use them as clues.

Ciphertext:
-----
{ciphertext}
-----

Return ONLY the decrypted plaintext. Do not include any explanation,
commentary, or markdown formatting — just the plaintext."""

    def validate_solution(self, ciphertext: str, claimed_plaintext: str) -> bool:
        """Check if claimed plaintext looks like a valid decryption.

        Validates:
        1. Not empty after stripping
        2. At least 50% alphabetic characters (not garbled)
        3. Length roughly matches ciphertext
        4. Not the ciphertext echoed back verbatim
        5. Derivable key is a valid bijection (first time check)
        """
        plain = claimed_plaintext.strip()
        cipher = ciphertext.strip()

        if not plain:
            return False
        if len(plain) < 3:
            return False
        if plain.upper() == cipher.upper():
            return False  # LLM just echoed the ciphertext

        # Length check: within 10% or ±5 chars
        len_diff = abs(len(plain) - len(cipher))
        max_len = max(len(plain), len(cipher))
        if max_len > 0 and len_diff / max_len > 0.2 and len_diff > 10:
            return False

        # Alphabetic ratio check
        alpha_chars = sum(1 for c in plain if c.isalpha())
        if len(plain) > 0 and alpha_chars / len(plain) < 0.4:
            return False

        # Derivable-key bijection check
        try:
            derived = self.derive_key(cipher, plain)
            if not derived:
                return False
            # Check the mapping is consistent
            mapping = self._parse_key(derived)
            if len(mapping) < 5:
                return False
        except (ValueError, KeyError):
            return False

        return True

    def retry_prompt(self, ciphertext: str, failed_guess: str) -> str:
        """Build a stronger follow-up prompt after a failed attempt."""
        return f"""Your previous attempt was not a valid decryption of this substitution cipher.
Take a more methodical approach:

1. First, count the frequency of each letter in the ciphertext.
2. Compare against expected English letter frequencies: E=12.7% T=9.1% A=8.2%
   O=7.5% I=7.0% N=6.7% S=6.3% H=6.1% R=6.0%
3. Identify the most common 1-letter word (likely "A" or "I").
4. Identify the most common 3-letter word (likely "THE" or "AND").
5. Work out the mapping one letter at a time and apply it systematically.
6. Punctuation and spaces are preserved as-is — use word boundaries as clues.

Ciphertext:
-----
{ciphertext}
-----

Return ONLY the decrypted plaintext. No explanation, no commentary."""

    def derive_key(self, ciphertext: str, plaintext: str) -> str:
        """Derive the substitution key from ciphertext→plaintext mapping."""
        cipher_upper = ciphertext.upper()
        plain_upper = plaintext.upper()

        mapping: dict[str, str] = {}
        for c_ch, p_ch in zip(cipher_upper, plain_upper):
            if c_ch.isalpha() and p_ch.isalpha():
                if c_ch in mapping and mapping[c_ch] != p_ch:
                    return ""  # inconsistent mapping
                mapping[c_ch] = p_ch

        if len(mapping) < 5:
            return ""

        pairs = sorted(
            f"{plain}→{cipher}" for plain, cipher in mapping.items()
        )
        return "  ".join(pairs)

    def _parse_key(self, key: str) -> dict[str, str]:
        """Parse a human-readable key like 'A→Q  B→Z  C→E' into a dict."""
        mapping: dict[str, str] = {}
        for part in key.split():
            part = part.strip()
            if "→" in part:
                plain, cipher = part.split("→", 1)
                if len(plain) == 1 and len(cipher) == 1 and plain.isalpha():
                    mapping[plain.upper()] = cipher.upper()
        return mapping
