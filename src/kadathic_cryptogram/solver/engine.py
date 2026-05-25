"""AI-powered cipher solver engine.

Orchestrates the solve flow: prompt → LLM → validate → retry.
When log_enabled, writes a detailed log file to solve_logs/.
"""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
from time import perf_counter
from typing import Union

from kadathic_cryptogram.backend.client import AgentFoundryClient, FakeAgentFoundryClient
from kadathic_cryptogram.ciphers.base import SolveResult
from kadathic_cryptogram.ciphers.registry import CipherRegistry

AgentClient = Union[AgentFoundryClient, FakeAgentFoundryClient]

LOG_DIR = Path("solve_logs")


class SolverEngine:
    """Orchestrate AI-powered cipher cracking with retry logic."""

    def __init__(
        self,
        client: AgentClient,
        cipher_registry: CipherRegistry,
        *,
        agent_id: str = "cryptogram_solver",
        max_retries: int = 3,
        log_enabled: bool = False,
    ) -> None:
        self._client = client
        self._cipher_registry = cipher_registry
        self._agent_id = agent_id
        self._max_retries = max_retries
        self._log_enabled = log_enabled

        if self._log_enabled:
            LOG_DIR.mkdir(parents=True, exist_ok=True)

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

        # Per-attempt logs (only collected when logging is enabled)
        attempt_logs: list[dict] = []

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

            passed = cipher.validate_solution(ciphertext, candidate)

            if self._log_enabled:
                attempt_logs.append({
                    "attempt": attempt,
                    "prompt": current_prompt,
                    "response": reply.text,
                    "response_len": len(reply.text),
                    "latency_ms": reply.latency_ms,
                    "provider": reply.provider_id or provider_id or "unknown",
                    "model": reply.model or "unknown",
                    "passed": passed,
                })

            if passed:
                derived_key = cipher.derive_key(ciphertext, candidate)
                total_latency = round((perf_counter() - total_started) * 1000)
                result = SolveResult(
                    plaintext=candidate,
                    success=True,
                    attempts=attempt,
                    total_latency_ms=total_latency,
                    derived_key=derived_key,
                    validation_details=details,
                )

                if self._log_enabled:
                    _write_log(
                        ciphertext=ciphertext,
                        cipher_type=cipher_type,
                        result=result,
                        attempt_logs=attempt_logs,
                    )

                return result

            details.append(f"Attempt {attempt}: validation FAILED")

        # All retries exhausted
        total_latency = round((perf_counter() - total_started) * 1000)
        result = SolveResult(
            plaintext="(Unable to solve — all attempts failed validation)",
            success=False,
            attempts=self._max_retries,
            total_latency_ms=total_latency,
            derived_key="",
            validation_details=details,
        )

        if self._log_enabled:
            _write_log(
                ciphertext=ciphertext,
                cipher_type=cipher_type,
                result=result,
                attempt_logs=attempt_logs,
            )

        return result


# ---------------------------------------------------------------------------
# Log file writing
# ---------------------------------------------------------------------------

_SEPARATOR = "=" * 80
_THIN = "-" * 80


def _write_log(
    *,
    ciphertext: str,
    cipher_type: str,
    result: SolveResult,
    attempt_logs: list[dict],
) -> None:
    """Write a single solve log file."""

    timestamp = datetime.now(UTC)
    filename = timestamp.strftime("solve_%Y%m%d_%H%M%S.log")
    path = LOG_DIR / filename

    provider = attempt_logs[0]["provider"] if attempt_logs else "unknown"
    model = attempt_logs[0]["model"] if attempt_logs else "unknown"

    lines: list[str] = []
    lines.append(_SEPARATOR)
    lines.append("Kadathic Cryptogram — Solve Log")
    lines.append(_SEPARATOR)
    lines.append(f"Timestamp:   {timestamp.strftime('%Y-%m-%d %H:%M:%S')} UTC")
    lines.append(f"Cipher type: {cipher_type}")
    lines.append(f"Provider:    {provider}")
    lines.append(f"Model:       {model}")
    lines.append(f"Ciphertext ({len(ciphertext)} chars):")
    # Show at most the first 500 chars of ciphertext
    preview = ciphertext if len(ciphertext) <= 500 else ciphertext[:500] + "..."
    lines.append(_indent(preview, 4))
    lines.append("")

    for entry in attempt_logs:
        n = entry["attempt"]
        lines.append(_THIN)
        lines.append(f"--- Attempt {n}/{len(attempt_logs)} ---")
        lines.append(_THIN)
        lines.append("")
        lines.append("PROMPT:")
        lines.append(_indent(entry["prompt"], 4))
        lines.append("")
        lines.append(
            f"RESPONSE ({entry['response_len']} chars, "
            f"latency={entry['latency_ms']}ms):"
        )
        lines.append(_indent(entry["response"], 4))
        lines.append("")
        status = "PASSED" if entry["passed"] else "FAILED"
        lines.append(f"VALIDATION: {status}")
        lines.append("")

    lines.append(_SEPARATOR)
    lines.append(
        f"RESULT: {'SUCCESS' if result.success else 'FAILED'} "
        f"after {result.attempts} attempt(s)"
    )
    lines.append(f"Total latency: {result.total_latency_ms}ms")
    lines.append(_SEPARATOR)
    lines.append("")

    path.write_text("\n".join(lines), encoding="utf-8")


def _indent(text: str, spaces: int) -> str:
    """Indent every line of text by *spaces* spaces."""
    prefix = " " * spaces
    return prefix + text.replace("\n", "\n" + prefix)
