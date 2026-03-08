# QuantTrader

Modular-monolith quantitative trading platform scaffold for US/HK equities and options.

## Current status
- ✅ Phase 1: core package scaffolding, interfaces, config, logging, DB abstraction, tests
- ✅ Phase 2: provider-agnostic market data layer with normalization, calendars, timezone handling, caching, retry/timeout, and tests
- ✅ Phase 3: broker abstraction, execution service, OMS state machine, trade fill processing, position updater, and risk guards
- ✅ Phase 4: modular strategy engine with event-driven/scheduled strategies, signal model, target model, and examples
- ✅ Phase 5: event-driven backtesting engine with costs, slippage, accounting, options hooks, and performance reporting
- ✅ Phase 6: production-focused risk framework (instrument/portfolio/market/options/operational controls)
- ✅ Phase 7: deployment and operations (Docker, compose, env, health, scheduler, runbook)

## Tech stack
- Python 3.12+
- Pydantic v2 / pydantic-settings
- Pytest

## Updated file tree

```text
.
├── AGENTS.md
├── ARCHITECTURE_VERSIONS.md
├── pyproject.toml
├── README.md
├── src/
│   └── quant_trader/
│       ├── __init__.py
│       ├── main.py
│       ├── adapters/
│       │   ├── __init__.py
│       │   ├── broker/
│       │   │   ├── __init__.py
│       │   │   └── in_memory.py
│       │   └── market_data/
│       │       ├── __init__.py
│       │       └── in_memory.py
│       ├── config/
│       │   ├── __init__.py
│       │   └── settings.py
│       ├── core/
│       │   ├── __init__.py
│       │   └── logging.py
│       ├── db/
│       │   ├── __init__.py
│       │   └── sqlite.py
│       ├── execution/
│       │   ├── __init__.py
│       │   └── service.py
│       ├── interfaces/
│       │   ├── __init__.py
│       │   ├── broker.py
│       │   ├── database.py
│       │   ├── market_data.py
│       │   ├── order_manager.py
│       │   ├── portfolio.py
│       │   ├── risk.py
│       │   └── strategy.py
│       ├── market_data/
│       │   ├── __init__.py
│       │   ├── cache.py
│       │   ├── calendar.py
│       │   ├── models.py
│       │   ├── service.py
│       │   └── symbols.py
│       ├── models/
│       │   ├── __init__.py
│       │   └── common.py
│       ├── oms/
│       │   ├── __init__.py
│       │   ├── order_manager.py
│       │   └── state_machine.py
│       ├── portfolio/
│       │   ├── __init__.py
│       │   └── updater.py
│       ├── risk/
│       │   ├── __init__.py
│       │   ├── framework.py
│       │   └── manager.py
│       ├── backtest/
│       │   ├── __init__.py
│       │   ├── accounting.py
│       │   ├── costs.py
│       │   ├── engine.py
│       │   ├── models.py
│       │   ├── options.py
│       │   └── performance.py
│       ├── ops/
│       │   ├── __init__.py
│       │   ├── alerting.py
│       │   ├── health.py
│       │   ├── migrations.py
│       │   ├── monitoring.py
│       │   └── scheduler.py
│       ├── strategy/
│       │   ├── __init__.py
│       │   ├── base.py
│       │   ├── engine.py
│       │   ├── models.py
│       │   ├── portfolio.py
│       │   └── examples/
│       │       ├── __init__.py
│       │       ├── covered_call.py
│       │       ├── hk_mean_reversion.py
│       │       ├── us_momentum.py
│       │       └── vol_breakout.py
│       └── utils/
│           ├── __init__.py
│           └── resilience.py
└── tests/
    ├── test_backtest_engine.py
    ├── test_backtest_options.py
    ├── test_interfaces.py
    ├── test_logging.py
    ├── test_market_calendar.py
    ├── test_market_data_service.py
    ├── test_market_data_symbols.py
    ├── test_ops_health_scheduler.py
    ├── test_ops_migrations_monitoring.py
    ├── test_order_manager_flow.py
    ├── test_order_state_machine.py
    ├── test_risk_framework.py
    ├── test_risk_manager.py
    ├── test_settings.py
    ├── test_sqlite_database.py
    ├── test_strategy_engine.py
    └── test_strategy_examples.py
```

## Phase 3 architecture updates

### Broker abstraction
- `BrokerInterface` defines submit/replace/cancel/get order, fill polling, and positions retrieval.
- `ExecutionService` isolates broker calls from OMS logic.

### OMS and lifecycle
- `OrderManager` owns order lifecycle, idempotency key checks, duplicate fill protection, and fill-driven status updates.
- `state_machine.py` validates legal transitions for acknowledged/partial/filled/canceled/replaced/rejected states.

### Risk and safety controls
`RiskManager` enforces:
- pre-trade checks
- max position size
- max order notional
- daily loss guard
- per-minute rate limit
- stale quote protection
- emergency kill switch

### Position updates
- `PortfolioPositionUpdater` mutates positions from fills and maintains weighted average price.

## Sample workflow (signal -> order -> fill -> position)

1. Strategy emits signal (outside phase 3 scope).
2. Portfolio builds `OrderRequest` with unique `idempotency_key`.
3. OMS `create_order()` calls risk manager pre-trade checks with latest quote.
4. On approval, execution submits to broker -> order enters `ACKNOWLEDGED`.
5. Broker emits fill(s) (partial/full).
6. OMS `process_fill()` updates order status (`PARTIALLY_FILLED`/`FILLED`) and average fill price.
7. Portfolio position updater applies fill and updates position quantity/average cost.
8. Duplicate fill ids or duplicate order idempotency keys are rejected.


## Phase 4 strategy engine updates

### Design
- `BaseStrategy` supports both event-driven (`on_event`) and scheduled (`on_schedule`) patterns.
- `StrategySignal` and `PositionTarget` models separate alpha generation from execution concerns.
- `StrategyEngine` orchestrates strategy execution and hands targets to portfolio construction + optional execution handoff.
- `StrategyContext` enables running the same strategy in `BACKTEST`, `PAPER`, and `LIVE` modes.

### Example strategies
- US equity momentum
- HK equity mean reversion
- Covered call (options)
- Options volatility breakout

### Sample strategy workflow
1. Receive market event or schedule trigger.
2. Strategy emits `StrategySignal` objects (alpha-only output).
3. `PortfolioConstructor` converts signals into `PositionTarget` objects.
4. `StrategyEngine` sends targets to execution handoff (OMS integration point).

## Phase 5 backtesting engine updates

### Features
- Event-driven backtest engine using chronological bar events.
- Historical bar support for US/HK equities and options symbols.
- Configurable slippage and commission/fee models.
- Calendar-aware run loop using trading-day checks.
- Portfolio accounting with cash, realized/unrealized PnL, and drawdown tracking.
- PnL attribution by instrument and asset class.
- Benchmark comparison and performance report generation.
- Option expiration handling with assignment/exercise extension hooks.

### No-lookahead and bias handling notes
- Default execution is **next-bar open** after signal generation to reduce lookahead bias.
- Survivorship-bias handling is **not automatic**; users must provide pre-curated historical universes when needed.

### Example backtest runs
- `python scripts/example_backtest_run.py`
- Use this script as a template to wire custom strategy engines and historical bars.

### Known limitations
- Corporate action adjustment is not automatic in this phase.
- Option lifecycle modeling is intentionally simplified by default hook behavior.
- Backtest state is in-memory; no persistence/replay store yet.

## Phase 6 risk framework updates

### Coverage
- Instrument-level controls: position limits.
- Portfolio-level controls: gross/net exposure, sector/group exposure, daily loss, strategy drawdown.
- Market-level controls: stale quote detection.
- Options-specific controls: greek thresholds and expiration risk checks.
- Operational controls: broker connectivity guard, max order-rate, duplicate order prevention, emergency stop workflow.
- Audit logging: allow/block decisions recorded for post-trade review.

### Example block scenarios
- Stale quote present for instrument -> order blocked.
- Broker connectivity unhealthy -> order blocked.
- Option greek exposure above limit -> order blocked.
- Option too close to expiry threshold -> order blocked.
- Duplicate idempotency key or order-rate breach -> order blocked.

## Phase 7 deployment and operations updates

### Deployment artifacts
- `Dockerfile` for containerized runtime.
- `docker-compose.yml` for local multi-service stack (app, scheduler, postgres).
- `.env.example` for environment variable management.
- `Makefile` for setup/test/run/docker/migrate workflows.

### Operational components
- Health checks (`scripts/healthcheck.py`, `ops.health`).
- Scheduler setup (`scripts/run_scheduler.py`, `ops.scheduler`).
- Monitoring hooks (`ops.monitoring.MetricsSink`).
- Alerting integration point (`ops.alerting.LoggingAlertSink`).
- Migration approach (`ops.migrations.MigrationRunner`, `scripts/migrate.py`, `db/migrations/*.sql`).

### Developer setup (quickstart)
1. `cp .env.example .env`
2. `make setup`
3. `make migrate`
4. `make run`
5. `make health`

### Docker local stack
1. `cp .env.example .env`
2. `make docker-up`
3. Verify `docker compose ps` health status
4. `make docker-down`

### Cloud-ready notes
- Build immutable image with `make docker-build`.
- Run app and scheduler as separate services.
- Use managed DB + secret manager in cloud environments.
- Execute migration job before rolling app deployment.

### Operational runbook
See `docs/OPS_RUNBOOK.md` for incident response, emergency stop workflow, health checks, migration operations, and audit/logging guidance.

## Setup

```bash
python3.12 -m venv .venv
source .venv/bin/activate
pip install -e .[dev]
```

## Run tests

```bash
pytest
```

## Assumptions and limitations
- In-memory broker/provider adapters are deterministic test adapters, not production execution connectors.
- OMS state is in-memory; persistent order store and reconciliation are future phases.
- Daily PnL updates for loss guard are injected via `RiskManager.update_daily_pnl()`.
- Calendar currently models regular sessions only.
- Cache is in-memory process-local.
