"""Tests for the solver engine."""

from kadathic_cryptogram.ciphers.registry import create_default_registry
from kadathic_cryptogram.ciphers.substitution import SubstitutionCipher
from kadathic_cryptogram.solver.engine import SolverEngine


class _FakeClientWithAnswers:
    """Fake client that returns canned replies for testing."""

    def __init__(self, replies: list[str]) -> None:
        self._replies = replies
        self._call_count = 0
        self.sent_messages: list[tuple[str, str]] = []

    def list_providers(self) -> list:
        from kadathic_cryptogram.backend.models import ProviderSummary
        return [ProviderSummary("mock", "mock", "mock-model")]

    def send_message(self, *, agent_id: str, user_message: str, provider_id: str | None = None):
        from kadathic_cryptogram.backend.models import ChatReply
        self.sent_messages.append((agent_id, user_message))
        idx = min(self._call_count, len(self._replies) - 1)
        text = self._replies[idx]
        self._call_count += 1
        return ChatReply(
            text=text,
            agent_id=agent_id,
            session_id="test-session",
            provider_id="mock",
            model="mock-model",
            latency_ms=5,
        )


class TestSolverEngine:
    def test_solve_success_first_attempt(self) -> None:
        """When the LLM returns correct plaintext, succeed on first attempt."""
        cipher = SubstitutionCipher()
        key = cipher.generate_key()
        plaintext = "HELLO WORLD THIS IS A TEST"
        ct = cipher.encrypt(plaintext, key)

        # Client returns the correct plaintext
        client = _FakeClientWithAnswers([plaintext])
        registry = create_default_registry()
        engine = SolverEngine(client, registry)

        result = engine.solve(ct, "substitution")
        assert result.success is True
        assert result.attempts == 1
        assert result.plaintext == plaintext
        assert result.derived_key != ""

    def test_solve_success_on_retry(self) -> None:
        """Succeed on second attempt when first fails."""
        cipher = SubstitutionCipher()
        key = cipher.generate_key()
        plaintext = "HELLO WORLD THIS IS A TEST"
        ct = cipher.encrypt(plaintext, key)

        # First reply is garbage, second is correct
        client = _FakeClientWithAnswers(["XYZXYZ XYZXYZ XYZ", plaintext])
        registry = create_default_registry()
        engine = SolverEngine(client, registry)

        result = engine.solve(ct, "substitution")
        assert result.success is True
        assert result.attempts == 2
        assert result.plaintext == plaintext

    def test_solve_fails_after_max_retries(self) -> None:
        """Return failure when all attempts fail validation."""
        cipher = SubstitutionCipher()
        key = cipher.generate_key()
        plaintext = "HELLO WORLD THIS IS A TEST"
        ct = cipher.encrypt(plaintext, key)

        # All replies are garbage
        garbage = ["GARBAGE ONE", "GARBAGE TWO", "GARBAGE THREE"]
        client = _FakeClientWithAnswers(garbage)
        registry = create_default_registry()
        engine = SolverEngine(client, registry, max_retries=3)

        result = engine.solve(ct, "substitution")
        assert result.success is False
        assert result.attempts == 3
        assert "unable to solve" in result.plaintext.lower()

    def test_tracks_attempt_count(self) -> None:
        """Verify the engine tracks attempt count correctly."""
        cipher = SubstitutionCipher()
        key = cipher.generate_key()
        pt = "HELLO WORLD"
        ct = cipher.encrypt(pt, key)

        client = _FakeClientWithAnswers(["BAD", pt])
        registry = create_default_registry()
        engine = SolverEngine(client, registry, max_retries=3)

        result = engine.solve(ct, "substitution")
        assert result.success is True
        assert result.attempts == 2

    def test_reports_latency(self) -> None:
        """Verify latency is tracked."""
        cipher = SubstitutionCipher()
        key = cipher.generate_key()
        pt = "HELLO WORLD"
        ct = cipher.encrypt(pt, key)

        client = _FakeClientWithAnswers([pt])
        registry = create_default_registry()
        engine = SolverEngine(client, registry)

        result = engine.solve(ct, "substitution")
        assert result.total_latency_ms >= 0

    def test_solve_preserves_punctuation(self) -> None:
        """Verify the solver works with punctuation in ciphertext."""
        cipher = SubstitutionCipher()
        key = cipher.generate_key()
        pt = "HELLO, WORLD! HOW ARE YOU?"
        ct = cipher.encrypt(pt, key)

        client = _FakeClientWithAnswers([pt])
        registry = create_default_registry()
        engine = SolverEngine(client, registry)

        result = engine.solve(ct, "substitution")
        assert result.success is True
        assert result.plaintext == pt
