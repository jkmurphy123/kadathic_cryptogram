# AGENTS.md

## Project: Kadathic Cryptogram

A NiceGUI utility app for creating and solving cipher puzzles (cryptograms),
backed by the Agent Foundry framework for AI-powered solving.

---

## Project Structure

```
kadathic_cryptogram/
  AGENTS.md
  DESIGN.md
  README.md
  pyproject.toml

  src/
    kadathic_cryptogram/
      __init__.py
      app.py               # NiceGUI app factory (create_app)
      main.py              # CLI entry points
      config.py            # FrontendConfig Pydantic model + YAML loader

      backend/
        client.py          # AgentFoundryClient (real) + FakeAgentFoundryClient
        models.py          # ProviderSummary, ChatReply dataclasses

      ciphers/
        base.py            # CipherProtocol, CipherResult, SolveResult
        substitution.py    # SubstitutionCipher implementation
        registry.py        # CipherRegistry + create_default_registry()

      solver/
        engine.py          # Solve orchestration: prompt → LLM → validate → retry (M2)

      state/
        app_state.py       # CryptogramUiState dataclass

      ui/
        shell.py           # 4-panel layout: top_bar + mode_panel + main + status_bar
        top_bar.py         # Provider / Model / Cipher selectors
        mode_panel.py      # Generate | Solve toggle buttons (left side)
        generate_panel.py  # Plaintext input → Generate → ciphertext output
        solve_panel.py     # Ciphertext input → Solve → plaintext output
        status_bar.py      # Status messages at the bottom

  tests/

  examples/
    agentfoundry.yaml.example
```

---

## Architecture Principles

1. **UI is dumb, backend is smart.** The NiceGUI frontend owns layout and event
   handling. Cipher logic is in `ciphers/`. AI solving is in `solver/`.
   The backend adapter is thin — just calls `AgentRuntime.chat()`.

2. **Cipher protocol.** Every cipher type implements `CipherProtocol`:
   `generate_key()`, `encrypt()`, `decrypt()`, `solve_prompt()`,
   `validate_solution()`, `retry_prompt()`, `derive_key()`.
   Adding a new cipher = one new module + register in `CipherRegistry`.

3. **Stateless solves.** Each solve call is a fresh, stateless session.
   No conversation history carries over between solve attempts.
   The prompt carries all the context the LLM needs.

4. **Validation before trust.** Every LLM solve attempt is validated:
   - Not empty / not the original ciphertext echoed back
   - Length roughly matches
   - Contains mostly alphabetic characters
   - Derivable key forms a consistent bijection

---

## Running

```bash
pip install -e .
kadathic-cryptogram --host 127.0.0.1 --port 8080
# or
python -m kadathic_cryptogram
```

---

## Milestones

### Milestone 1 (current) — Skeleton + Substitution Generate
- Project scaffolding, config, state, cipher protocol, substitution cipher
- UI shell with 4-panel layout
- Generate mode fully wired (local, no LLM needed)
- Solve mode placeholder UI
- Tests for cipher and config

### Milestone 2 — AI-Powered Solve
- Agent definition (cryptogram_solver)
- SolverEngine with prompt → validate → retry loop
- Solve panel wired to real backend
- Integration test: generate → solve → compare

### Milestone 3 — Polish
- Better error handling, copy-to-clipboard
- Additional cipher types (Caesar, Atbash)

---

## Do Not

- Do not put AI logic in UI components. Cipher logic goes in `ciphers/`,
  solver logic in `solver/`.
- Do not store session state between solves. Each solve is independent.
- Do not call `AgentRuntime` directly from UI code. Use the backend client.
- Do not hardcode provider/model names in UI. Use config.
