# AGENTS.md

## Scope
This file defines coding and architecture rules for the entire repository.

## Architecture rules
1. Keep a modular-monolith architecture with explicit interface boundaries.
2. Strategies must not call broker or market-data adapters directly; only orchestration/services may do that.
3. All order submissions must pass through risk checks before reaching the broker layer.
4. Use strongly typed models (`pydantic` models for external/config/data contracts).
5. Keep components replaceable via interfaces in `quant_trader.interfaces`.

## Coding rules
1. Python 3.12+ only.
2. Type hints are required for all public functions, methods, and attributes.
3. Public modules/classes/functions must have docstrings.
4. Prefer standard library unless a dependency clearly improves correctness.
5. Avoid global mutable state; dependency injection through constructors is preferred.
6. Logging must use the central logger configuration in `quant_trader.core.logging`.

## Testing rules
1. Every new module should have at least one automated test path.
2. Tests must be deterministic and avoid external network dependencies.
3. Use `pytest` and keep test fixtures minimal and explicit.

## Safety rules
1. Never bypass risk interfaces in trading workflows.
2. Never hardcode secrets in source files.
3. Validate environment-driven configuration at startup.
