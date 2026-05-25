"""AI-powered cipher solver engine.

Orchestrates the solve flow: prompt → LLM → validate → retry.
"""

from __future__ import annotations

from time import perf_counter
from typing import Union

from kadathic_cryptogram.backend.client import AgentFoundryClient, FakeAgentFoundryClient
from kadathic_cryptogram.ciphers.base import SolveResult
from kadathic_cryptogram.ciphers.registry import CipherRegistry

AgentClient = Union[AgentFoundryClient, FakeAgentFoundryClient]


class SolverEngine:
    """Orchestrate AI-powered cipher cracking with retry logic."""

    def __init__(
        self,
        client: AgentClient,
        cipher_registry: CipherRegistry,
        *,
        agent_id: str = "cryptogram_solver",
        max_retries: int = 3,
    ) -> None:
        self._client = client
        self._cipher_registry = cipher_registry
        self._agent_id = agent_id
        self._max_retries = max_retries

    def solve(
        self,
        ciphertext: str,
        cipher_type: str,
        *,
        provider_id: str | None = None,
    ) -> SolveResult:
        """Attempt to crack the ciphertext, retrying if validation fails.

        Args:
            ciphertext: The encrypted text to solve.
            cipher_type: The cipher type (e.g. "substitution").
            provider_id: Optional provider override.

        Returns:
            SolveResult with plaintext, success flag, attempt count, and latency.
        """

        cipher = self._cipher_registry.get(cipher_type)
        total_started = perf_counter()
        details: list[str] = []
        current_prompt: str | None = None

        for attempt in range(1, self._max_retries + 1):
            if attempt == 1:
                current_prompt = cipher.solve_prompt(ciphertext)
            else:
                current_prompt = cipher.retry_prompt(
                    ciphertext, "(previous attempt failed validation)"
                )

            reply = self._client.send_message(
                agent_id=self._agent_id,
                user_message=current_prompt,
                provider_id=provider_id,
            )

            candidate = reply.text.strip()
            details.append(
                f"Attempt {attempt}: {len(candidate)} chars, "
                f"latency={reply.latency_ms}ms"
            )

            if cipher.validate_solution(ciphertext, candidate):
                derived_key = cipher.derive_key(ciphertext, candidate)
                total_latency = round((perf_counter() - total_started) * 1000)
                return SolveResult(
                    plaintext=candidate,
                    success=True,
                    attempts=attempt,
                    total_latency_ms=total_latency,
                    derived_key=derived_key,
                    validation_details=details,
                )

            details.append(f"Attempt {attempt}: validation FAILED")

        # All retries exhausted
        total_latency = round((perf_counter() - total_started) * 1000)
        return SolveResult(
            plaintext="(Unable to solve — all attempts failed validation)",
            success=False,
            attempts=self._max_retries,
            total_latency_ms=total_latency,
            derived_key="",
            validation_details=details,
        )
