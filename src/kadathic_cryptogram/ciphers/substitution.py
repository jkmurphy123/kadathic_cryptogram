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

    def build_hint_prompt(
        self, ciphertext: str, candidate: str, known_plaintext: str
    ) -> str:
        """Build a prompt showing which parts of the LLM's attempt are correct.

        Includes a positional mask (correct letters stay, wrong become dashes),
        a stacked ciphertext-above-mask view for column-by-column reading,
        and the verified cipher→plain mappings the LLM got right.
        """

        # --- 1. Positional mask ---
        min_len = min(len(candidate), len(known_plaintext))
        mask_chars: list[str] = []
        correct_count = 0
        total_alpha = 0

        for i in range(min_len):
            c = candidate[i]
            k = known_plaintext[i]
            if c in (" ", ".", ",", "!", "?", ";", ":", "-", "'", '"'):
                mask_chars.append(c)
            elif c.upper() == k.upper():
                mask_chars.append(c)
                if c.isalpha():
                    correct_count += 1
            else:
                mask_chars.append("-")

        # Count total alphabetic positions for percentage
        total_alpha = sum(1 for i in range(min_len) if known_plaintext[i].isalpha())

        if len(candidate) > min_len:
            mask_chars.append("…")
        masked = "".join(mask_chars)

        # --- 2. Stacked ciphertext / mask view ---
        ciph_chars: list[str] = []
        mask_row: list[str] = []

        for i in range(min_len):
            cc = ciphertext[i] if i < len(ciphertext) else " "
            mc = mask_chars[i] if i < len(mask_chars) else " "

            # Keep columns aligned: pad shorter strings with spaces
            ciph_chars.append(cc)
            mask_row.append(mc)

        # Break into lines of ~60 chars for readability
        stacked_lines: list[str] = []
        columns_per_line = 60
        for start in range(0, min_len, columns_per_line):
            end = min(start + columns_per_line, min_len)
            stacked_lines.append(
                "Cipher:  " + " ".join(ciph_chars[start:end])
            )
            stacked_lines.append(
                "Plain:   " + " ".join(mask_row[start:end])
            )
            stacked_lines.append("")

        # --- 3. Verified mappings ---
        cipher_upper = ciphertext.upper()
        known_upper = known_plaintext.upper()
        candidate_upper = candidate.upper()

        verified: dict[str, str] = {}  # cipher_char → plaintext_char
        for i in range(min_len):
            cc = cipher_upper[i] if i < len(cipher_upper) else ""
            ca = candidate_upper[i] if i < len(candidate_upper) else ""
            kn = known_upper[i] if i < len(known_upper) else ""

            if cc.isalpha() and ca == kn and ca.isalpha():
                verified[cc] = kn

        mapping_lines: list[str] = []
        if verified:
            for cipher_ch in sorted(verified):
                mapping_lines.append(
                    f"  {cipher_ch} → {verified[cipher_ch]}"
                )

        # --- 4. Build the prompt ---
        pct = round(correct_count / max(total_alpha, 1) * 100)
        parts: list[str] = []

        parts.append(
            f"Your previous attempt got {correct_count} of "
            f"{total_alpha} letters correct ({pct}%). "
            "Here is your progress:"
        )
        parts.append("")

        parts.append(
            "The ciphertext and your partial plaintext are stacked below — "
            "read column-by-column to see each cipher→plain pair:"
        )
        parts.extend(stacked_lines)

        parts.append("VERIFIED MAPPINGS — these are correct everywhere:")
        if mapping_lines:
            parts.extend(mapping_lines)
            parts.append("")
            parts.append(
                f"Each mapping above applies to EVERY occurrence of that "
                f"cipher letter in the text."
            )
        else:
            parts.append("  (none verified yet)")
            parts.append("")

        parts.append(
            "CORRECT LETTERS SHOWN; INCORRECT REPLACED WITH '-':"
        )
        parts.append(masked)
        parts.append("")

        parts.append(
            "Use the correct letters and verified mappings as anchors. "
            "Deduce the remaining dashes using partial words as clues. "
            "Return ONLY the complete decrypted plaintext. No explanation."
        )

        return "\n".join(parts)

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
