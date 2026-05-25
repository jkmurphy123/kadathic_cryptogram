"""Tests for the substitution cipher implementation."""

import pytest

from kadathic_cryptogram.ciphers.substitution import SubstitutionCipher


@pytest.fixture
def cipher() -> SubstitutionCipher:
    return SubstitutionCipher()


class TestSubstitutionCipher:
    def test_generate_key_has_all_letters(self, cipher: SubstitutionCipher) -> None:
        key = cipher.generate_key()
        # Should have 26 pairs
        pairs = [p for p in key.split("  ") if "→" in p]
        assert len(pairs) == 26
        # Each plain letter A-Z should appear
        plain_letters = {p.split("→")[0].strip() for p in pairs}
        assert plain_letters == set("ABCDEFGHIJKLMNOPQRSTUVWXYZ")
        # Each cipher letter should be unique
        cipher_letters = {p.split("→")[1].strip() for p in pairs}
        assert len(cipher_letters) == 26

    def test_key_is_random(self, cipher: SubstitutionCipher) -> None:
        key1 = cipher.generate_key()
        key2 = cipher.generate_key()
        # Extremely unlikely to be identical
        assert key1 != key2

    def test_encrypt_decrypt_roundtrip(self, cipher: SubstitutionCipher) -> None:
        key = cipher.generate_key()
        plaintext = "THE QUICK BROWN FOX JUMPS OVER THE LAZY DOG"
        ciphertext = cipher.encrypt(plaintext, key)
        # Ciphertext should differ from plaintext
        assert ciphertext != plaintext
        # All original non-letters preserved
        assert len(ciphertext) == len(plaintext)
        # Decrypt should recover original
        decrypted = cipher.decrypt(ciphertext, key)
        assert decrypted == plaintext

    def test_encrypt_preserves_non_letters(self, cipher: SubstitutionCipher) -> None:
        key = cipher.generate_key()
        plaintext = "Hello, World! 123..."
        ciphertext = cipher.encrypt(plaintext, key)
        # Commas, spaces, digits should be preserved
        assert "," in ciphertext
        assert " " in ciphertext
        assert "123" in ciphertext

    def test_encrypt_is_consistent(self, cipher: SubstitutionCipher) -> None:
        key = cipher.generate_key()
        ct1 = cipher.encrypt("AAA", key)
        ct2 = cipher.encrypt("AAA", key)
        assert ct1 == ct2  # Same key, same output

    def test_decrypt_same_key(self, cipher: SubstitutionCipher) -> None:
        key = cipher.generate_key()
        plaintext = "TESTING ONE TWO THREE"
        ct = cipher.encrypt(plaintext, key)
        pt = cipher.decrypt(ct, key)
        assert pt == plaintext


class TestValidateSolution:
    def test_accepts_correct_solution(self, cipher: SubstitutionCipher) -> None:
        key = cipher.generate_key()
        plaintext = "THE QUICK BROWN FOX JUMPS OVER THE LAZY DOG"
        ct = cipher.encrypt(plaintext, key)
        assert cipher.validate_solution(ct, plaintext)

    def test_rejects_empty(self, cipher: SubstitutionCipher) -> None:
        assert not cipher.validate_solution("ANYTHING", "")
        assert not cipher.validate_solution("ANYTHING", "   ")

    def test_rejects_ciphertext_echo(self, cipher: SubstitutionCipher) -> None:
        ct = "WXTTN DNFTS"
        assert not cipher.validate_solution(ct, ct)

    def test_rejects_garbled_text(self, cipher: SubstitutionCipher) -> None:
        key = cipher.generate_key()
        pt = "HELLO WORLD THIS IS A TEST MESSAGE FOR VALIDATION"
        ct = cipher.encrypt(pt, key)
        # Pass garbage that has wrong letter ratio
        assert not cipher.validate_solution(ct, "12345 67890 !@#$% ^&*()")

    def test_rejects_wrong_length(self, cipher: SubstitutionCipher) -> None:
        key = cipher.generate_key()
        pt = "A" * 100
        ct = cipher.encrypt(pt, key)
        assert not cipher.validate_solution(ct, "SHORT")


class TestDeriveKey:
    def test_derive_key_from_correct_mapping(self, cipher: SubstitutionCipher) -> None:
        key = cipher.generate_key()
        plaintext = "HELLO WORLD"
        ct = cipher.encrypt(plaintext, key)
        derived = cipher.derive_key(ct, plaintext)
        assert derived
        assert "→" in derived

    def test_derive_key_inconsistent_fails(self, cipher: SubstitutionCipher) -> None:
        # Plaintext where same cipher char maps to two different chars
        ct = "ABC"
        pt = "XYX"  # B maps to both Y and nothing consistent
        # Actually, X→A, Y→B, X→C — B maps to Y and C maps to X is fine because
        # we map cipher→plain. Let's reverse: try inconsistent
        ct2 = "ABA"  # A maps to two different plain letters
        pt2 = "XYZ"  # A→X, B→Y, A→Z — inconsistent!
        derived = cipher.derive_key(ct2, pt2)
        assert derived == ""


class TestSolvePrompt:
    def test_solve_prompt_contains_ciphertext(self, cipher: SubstitutionCipher) -> None:
        ct = "SOME ENCRYPTED TEXT"
        prompt = cipher.solve_prompt(ct)
        assert ct in prompt
        assert "frequency analysis" in prompt.lower()
        assert "THE" in prompt

    def test_retry_prompt_contains_ciphertext(self, cipher: SubstitutionCipher) -> None:
        ct = "SOME ENCRYPTED TEXT"
        prompt = cipher.retry_prompt(ct, "bad guess")
        assert ct in prompt
        assert "methodical" in prompt.lower()
