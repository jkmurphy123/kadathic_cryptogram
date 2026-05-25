# Kadathic Cryptogram — Design Document

## Overview

A NiceGUI utility app for creating and solving cipher puzzles (cryptograms),
like those found in puzzle magazines. Two modes:

1. **Generate** — pick a cipher type, enter plaintext, get encrypted ciphertext + key.
2. **Solve** — paste ciphertext, let the AI (via the kadathic Agent Foundry framework)
   crack it by reasoning about the cipher.

The generate side is pure Python cryptography. The solve side uses the Agent
Foundry backend (`AgentRuntime.chat()`) to send the puzzle to an LLM agent with
a carefully crafted prompt. If the LLM's answer fails validation, the app retries
with a more directive prompt.

---

## Core Modules

```
kadathic_cryptogram/
  DESIGN.md               ← this file
  PROJECT_DESIGN.md       ← frozen copy once design is approved
  AGENTS.md               ← AI agent guidance for this project
  README.md
  pyproject.toml

  src/
    kadathic_cryptogram/
      __init__.py
      app.py               # NiceGUI app factory
      main.py              # CLI entry points
      config.py            # FrontendConfig model + loader

      backend/
        __init__.py
        client.py          # Thin adapter around AgentRuntime
        models.py          # UI-safe dataclasses

      ciphers/
        __init__.py
        base.py            # CipherProtocol, CipherResult
        substitution.py    # Simple substitution cipher
        registry.py        # CipherRegistry — pluggable cipher types

      solver/
        __init__.py
        engine.py          # Solve orchestration: prompt → LLM → validate → retry
        prompts.py         # Prompt templates for each cipher type
        validator.py       # Validation logic per cipher type

      state/
        __init__.py
        app_state.py       # CryptogramUiState — local UI state

      ui/
        __init__.py
        shell.py           # Top-level 4-panel layout
        top_bar.py         # Provider / Model / Cipher selectors
        mode_panel.py      # Generate | Solve toggle (left side)
        generate_panel.py  # Plaintext input + Generate button + ciphertext output
        solve_panel.py     # Ciphertext input + Solve button + plaintext output
        status_bar.py      # Status messages, latency, provider info

  tests/
    test_cipher_substitution.py
    test_solver_engine.py
    test_solver_validator.py
    test_config.py

  examples/
    agentfoundry.yaml.example
```

---

## Cipher Protocol

Every cipher type implements a common protocol. This makes adding Caesar,
Vigenere, Atbash, etc. trivial later — just write one new module and register it.

```python
from dataclasses import dataclass
from typing import Protocol

@dataclass(frozen=True)
class CipherResult:
    """Result of generating an encrypted text from plaintext."""
    plaintext: str
    ciphertext: str
    key: str              # human-readable key (e.g. "A→Q B→Z C→E ...")
    cipher_type: str      # "substitution"

class CipherProtocol(Protocol):
    """Contract every cipher must satisfy."""

    cipher_type: str      # unique id, e.g. "substitution"

    def generate_key(self) -> str:
        """Return a random key string for this cipher type."""
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
        """Check if a claimed plaintext is a valid decryption of the ciphertext."""
        ...

    def retry_prompt(self, ciphertext: str, failed_guess: str) -> str:
        """Return a stronger follow-up prompt when the first attempt failed."""
        ...
```

A `CipherRegistry` (simple dict of `{cipher_type: CipherProtocol}`) makes
the UI dropdown auto-populated.

---

## Simple Substitution Cipher — Details

The first cipher type to implement.

**Key generation:**
- Create a random permutation of the 26 uppercase letters.
- The key is the mapping string: `A→Q B→Z C→E ... Z→M` (26 pairs).
- Internally stored as two dicts: `{plain_letter: cipher_letter}` and its inverse.

**Encryption:**
- Uppercase the plaintext, strip non-alphabetic characters (or preserve punctuation
  as-is — design choice: preserve punctuation and spaces, only encrypt A-Z).
- Replace each letter with its mapped counterpart.
- Non-letters pass through unchanged.

**Decryption (deterministic, used only for validation):**
- Apply the inverse mapping.

**Prompt for AI solve (first attempt):**

```
You are a cryptography expert. Below is a ciphertext encrypted with a simple
mono-alphabetic substitution cipher. Each letter in the original message has been
replaced by a different letter, consistently throughout the text.

Your task: Decrypt the ciphertext back to the original English plaintext.

- Use frequency analysis: 'E' is the most common letter in English,
  followed by 'T', 'A', 'O', 'I', 'N', 'S', 'H', 'R'.
- Look for common short words: "THE", "AND", "A", "I", "TO", "OF", "IN".
- Look for repeated patterns, double letters, and apostrophe patterns.
- The plaintext will be coherent English.

Ciphertext:
-----
{ciphertext}
-----

Return ONLY the decrypted plaintext. Do not include any explanation,
commentary, or markdown formatting — just the plaintext.
```

**Validation:**

After the LLM returns a candidate plaintext:
1. Strip whitespace, check it's not empty.
2. Check it contains at least 60% alphabetic characters (not garbled).
3. Check character length matches ciphertext (±2 for possible whitespace trimming).
4. Check it doesn't contain the original ciphertext verbatim (LLM may just echo).
5. (Optional, stronger) Try to derive a key mapping from ciphertext→claimed plaintext
   and check the mapping is a valid bijection. If letters map inconsistently, fail.

**Retry prompt (if first attempt fails validation):**

```
Your previous attempt did not appear to be a valid decryption. Take a more
methodical approach:

1. First, count the frequency of each letter in the ciphertext.
2. Compare against expected English letter frequencies: E=12.7% T=9.1% A=8.2%
   O=7.5% I=7.0% N=6.7% S=6.3% H=6.1% R=6.0%
3. Identify the most common 1-letter word (likely "A" or "I").
4. Identify the most common 3-letter word (likely "THE" or "AND").
5. Work out the mapping one letter at a time and apply it systematically.

Ciphertext:
-----
{ciphertext}
-----

Return ONLY the decrypted plaintext. No explanation.
```

**Max retries:** 3 attempts before giving up and showing the last attempt.

---

## Solver Engine

Orchestrates the AI solve flow:

```python
class SolverEngine:
    def __init__(self, client: AgentFoundryClient):
        self._client = client
        self._max_retries = 3

    def solve(
        self,
        ciphertext: str,
        cipher_type: str,
        provider_id: str | None = None,
    ) -> SolveResult:
        """Return (plaintext, attempts, success) after up to max_retries."""
```

Flow:
1. Get the `solve_prompt(ciphertext)` from the cipher registry.
2. Send it to the Agent Foundry backend via `client.send_message()`.
3. Extract the LLM's response text.
4. Validate with `cipher.validate_solution(ciphertext, response_text)`.
5. If valid → return success.
6. If not valid and retries remain → get `retry_prompt()`, send again.
7. If out of retries → return last attempt with `success=False`.

The `SolveResult` carries:
- `plaintext: str` — the best decryption (or the last attempt)
- `success: bool`
- `attempts: int` — how many LLM calls were made
- `total_latency_ms: int` — combined LLM latency
- `validation_details: list[str]` — why each attempt passed or failed

---

## Backend Client Adapter

Follow the same pattern as `kadathic_chat`. Thin adapter, no business logic:

```python
class AgentFoundryClient:
    def __init__(self, project_config_path: str | Path): ...

    def list_providers(self) -> list[ProviderSummary]: ...

    def send_message(
        self,
        *,
        agent_id: str,
        user_message: str,
        provider_id: str | None = None,
    ) -> ChatReply: ...
```

Key differences from the chatbot client:
- No session management needed (each solve is stateless — no conversation
  history matters between solves).
- We use a dedicated agent (e.g., `cryptogram_solver`) defined in `agentfoundry.yaml`
  with a personality that knows it's a cipher solver.
- `send_message()` uses `AppContext.simple()` with `app_type="cryptogram"` and
  a `state_summary` that describes the task.

The `FakeAgentFoundryClient` returns deterministic replies for unit tests.

---

## UI Layout

Same 4-panel shell pattern as `kadathic_chat`:

```
┌──────────────────────────────────────────────────────────────────────┐
│ TOP BAR                                                              │
│ [Provider ▼]  [Model ▼]  [Cipher ▼]                                  │
├───────────────┬──────────────────────────────────────────────────────┤
│ MODE PANEL    │ MAIN PANEL                                           │
│               │                                                      │
│ ● Generate    │  ┌──────────────────────────────────────────────┐    │
│               │  │ Plaintext (multi-line textarea)              │    │
│ ○ Solve       │  │                                              │    │
│               │  │                                              │    │
│               │  └──────────────────────────────────────────────┘    │
│               │  [Generate]                                         │
│               │                                                      │
│               │  ┌──────────────────────────────────────────────┐    │
│               │  │ Ciphertext output (read-only multi-line)     │    │
│               │  │                                              │    │
│               │  └──────────────────────────────────────────────┘    │
│               │  Key: A→Q B→Z C→E ... (shown below output)          │
├───────────────┴──────────────────────────────────────────────────────┤
│ STATUS BAR                                                            │
│ Status: ready | Provider: deepseek | Model: deepseek-v4 | Latency: —  │
└──────────────────────────────────────────────────────────────────────┘
```

**Left side — Mode Panel (fixed-width, ~160px):**
- Radio-button or segmented-button style toggle: "Generate" / "Solve".
- Only one mode is active at a time. Swapping modes swaps the right-side content.

**Right side — Main Panel (grows to fill):**

*Generate mode:*
1. Multi-line textarea for plaintext input (placeholder: "Enter your message...")
2. "Generate" button
3. Status spinner while generating (local, instant, no LLM needed)
4. Multi-line textarea for ciphertext output (read-only, selectable for copy)
5. Key display below the ciphertext (monospaced, e.g. `A→Q  B→Z  C→E  D→R  ...`)

*Solve mode:*
1. Multi-line textarea for ciphertext input (placeholder: "Paste encrypted text...")
2. "Solve" button
3. Status spinner with live attempts counter ("Attempt 1/3...")
4. Multi-line textarea for plaintext output (read-only, selectable for copy)
5. If solve fails: show last attempt + warning "Could not crack. Try again?"
6. Latency and attempt count displayed below output

**Bottom — Status Bar:**
- Reusable from `kadathic_chat` pattern.
- Shows: status, provider, model, cipher type, latency, errors.

---

## State Model

```python
from dataclasses import dataclass, field
from enum import Enum

class AppMode(str, Enum):
    GENERATE = "generate"
    SOLVE = "solve"

class CipherType(str, Enum):
    SUBSTITUTION = "substitution"

@dataclass
class CryptogramUiState:
    # Selectors
    selected_provider_id: str | None = None
    selected_model: str | None = None
    selected_cipher: CipherType = CipherType.SUBSTITUTION

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

    # General
    is_busy: bool = False
    status: str = "ready"
    last_error: str | None = None
    last_provider: str | None = None
    last_latency_ms: int | None = None
```

---

## Configuration

```yaml
# frontend.yaml
backend:
  project_config_path: ./agentfoundry.yaml
  project_id: cryptogram_project
  default_user_id: local-user

ui:
  title: Kadathic Cryptogram
  default_provider_id: deepseek
  default_cipher: substitution

solve:
  agent_id: cryptogram_solver
  max_retries: 3
```

The `SolveConfig` controls solver behavior and the agent used.

---

## Agent Foundry Integration

A new agent `cryptogram_solver` is defined in the project's `agentfoundry.yaml`:

```yaml
project:
  id: cryptogram_project
  name: Kadathic Cryptogram

agents:
  libraries:
    - ./agents

providers:
  deepseek:
    type: deepseek
    model: deepseek-chat
    api_key: ${DEEPSEEK_API_KEY}

context_policy:
  max_recent_messages: 3
```

The agent definition (`agents/cryptogram_solver/agent.yaml` + `personality.md`)
gives the LLM its baseline identity. The app's prompt overrides the user_message
with the solve prompt, which is the primary instruction. The agent personality
just says "You are a helpful cipher-solving assistant."

---

## Prompt Strategy

The app controls prompting, not the agent personality. The flow:

1. User clicks Solve.
2. App calls `cipher.solve_prompt(ciphertext)` → gets the full prompt.
3. App calls `client.send_message(agent_id="cryptogram_solver", user_message=prompt)`.
4. The Agent Foundry runtime assembles context (personality + policy + prompt +
   app_context with type="cryptogram") and sends to the provider.
5. LLM responds with plaintext (or something).
6. App validates. If fails → `cipher.retry_prompt()` → send again.

The `AppContext` state_summary tells the agent what mode we're in:
```
"Cryptogram solver session. User is providing ciphertext encrypted with
a simple substitution cipher. Decrypt it and return only the plaintext."
```

---

## Running the App

```bash
cd /home/ubuntu/ai_projects/kadathic_cryptogram
pip install -e .
kadathic-cryptogram
# or
python -m kadathic_cryptogram
```

CLI options:
```bash
kadathic-cryptogram --config ./frontend.yaml --host 127.0.0.1 --port 8080
```

---

## Milestone Plan

### Milestone 1 — Skeleton & Substitution Generate
- Project scaffolding (pyproject.toml, directory structure, AGENTS.md).
- Config model + loader.
- Backend models + FakeClient.
- CipherProtocol + SubstitutionCipher (generate_key, encrypt, decrypt).
- UI shell (top_bar, mode_panel, status_bar) with static layout.
- Generate panel wired up (no LLM needed).
- Basic unit tests for cipher.

### Milestone 2 — AI-Powered Solve
- Agent definition (`cryptogram_solver` with personality.md).
- `agentfoundry.yaml` with real provider config.
- SolverEngine with prompt → validate → retry loop.
- Solve panel wired up with real backend.
- Validation logic for substitution cipher.
- Integration test: generate → solve → compare.

### Milestone 3 — Polish & Robustness
- Better error handling and user feedback.
- Attempts counter display during solve.
- Copy-to-clipboard buttons for outputs.
- Solve validation improvements (bijection check).
- Additional cipher types (Caesar, Atbash) — plug-and-play via registry.

---

## Confirmed Design Decisions

1. ✅ **Punctuation:** Preserve spaces and punctuation in ciphertext as-is.
   Non-letters pass through unchanged. Helps the LLM use word boundaries.

2. ✅ **Case:** Ciphertext is uppercase (cryptogram standard). Plaintext
   displayed in sentence case after decryption.

3. ✅ **Key display:** Human-readable, space-separated pairs in monospaced font,
   e.g. `A→Q  B→Z  C→E  D→R  ...`

4. ✅ **Text length:** Capped at ~2000 chars for LLM solve. Minimum ~50 chars
   for reliable frequency analysis. Warn if below minimum.

5. ✅ **Derived key on solve:** After a successful AI solve, derive the mapping
   from ciphertext→claimed_plaintext and display it alongside the answer so
   the user can review/verify.

---

*Design by Hermes — pending user review before implementation.*
