# Quantitative Trading System Architectures (US + HK, Equities + Options)

## Executive summary
This document proposes four production-oriented architectures for a multi-market systematic trading platform covering US stocks, Hong Kong stocks, US stock options, and HK derivatives/options when supported by broker and data vendors.

- **Version A (Solo Monolith)**: fastest path for one developer; single deployable service with clean module boundaries.
- **Version B (Scalable Event-Driven)**: microservice/event-bus design for horizontal scaling and low coupling.
- **Version C (Research-First)**: optimized for factor research, options analytics, and reproducible backtests.
- **Version D (Production-First)**: reliability/risk-governance-first architecture with strict controls and operational safety.

All four include broker/data abstraction, strategy + portfolio + risk + OMS, backtest/paper/live modes, options analytics (greeks/IV/surface/chains), persistence, scheduling/event processing, observability, and safety controls (kill switch/max loss/limits/stale data).

---

## Version A — Simplest architecture for a solo developer

### 1) High-level design
A **modular monolith** in Python:
- One codebase, one runtime process (or a few background workers)
- Shared PostgreSQL + Redis
- Internal event bus (in-memory queues) to decouple components
- Mode switch: `backtest | paper | live`

This minimizes DevOps burden while preserving clean boundaries for future extraction into services.

### 2) Folder structure
```text
quant-platform/
  pyproject.toml
  docker-compose.yml
  .env.example
  src/
    app/
      main.py                  # process bootstrap
      config/
        settings.py
        feature_flags.py
      core/
        events.py
        scheduler.py
        clock.py
      adapters/
        brokers/
          base.py
          ibkr.py
          alpaca.py
        data/
          base.py
          polygon.py
          ibkr_market_data.py
      market/
        instruments.py         # stock/option/future schema
        calendars.py           # US/HK sessions + holidays
        option_chain.py
        greeks.py
        iv_surface.py
      strategy/
        base.py
        signals/
        examples/
      portfolio/
        positions.py
        pnl.py
        accounting.py
      risk/
        rules.py               # max loss, limits, stale data guards
        kill_switch.py
      oms/
        order_router.py
        state_machine.py
      execution/
        paper_broker.py
        live_executor.py
      backtest/
        engine.py
        fills.py
        slippage.py
      research/
        factors.py
        walk_forward.py
        reports.py
      storage/
        models.py
        repositories.py
        migrations/
      observability/
        logging.py
        metrics.py
        alerts.py
  tests/
  notebooks/
  scripts/
```

### 3) Core modules
- **Broker abstraction layer**: unified API (`get_positions`, `submit_order`, `cancel_order`, `get_option_chain`).
- **Market data abstraction**: normalized ticks/bars/quotes/options chain snapshots.
- **Strategy engine**: signal generation over event stream.
- **Portfolio management**: holdings, exposures, realized/unrealized PnL.
- **Risk engine**: pre-trade and post-trade checks.
- **OMS**: order lifecycle + broker routing.
- **Backtester**: same strategy interface, historical replay clock.
- **Mode controller**: config-selectable paper/live/backtest adapters.

### 4) Data flow
1. Scheduler wakes market sessions (US/HK).
2. Data adapter pulls/streams quotes/trades/chains.
3. Strategy computes signals.
4. Portfolio proposes target trades.
5. Risk checks (limits, stale data, kill switch state).
6. OMS creates child orders and routes to execution adapter.
7. Fills update positions + PnL + risk.
8. Logs/metrics/alerts emitted.

### 5) How options are modeled
- `Instrument` with fields: `asset_class`, `underlying`, `expiry`, `strike`, `right`, `multiplier`, `exchange`, `currency`.
- `OptionQuote`: bid/ask/last, mid, timestamp.
- `OptionGreeks`: delta/gamma/vega/theta/rho + model inputs.
- `VolSurface`: by tenor/strike or tenor/delta grid.
- `OptionChain`: versioned snapshots keyed by timestamp and underlying.
- Pricing model plug-ins: Black-Scholes (equity), local-vol/surface interpolation.

### 6) Pros
- Fastest to build and debug.
- Lowest infrastructure complexity.
- Easy local and Docker deployment.

### 7) Cons
- Limited horizontal scalability.
- Process failure can affect all functions.
- Harder to isolate noisy components.

### 8) Best use case
Solo founder building MVP-to-early-production with moderate strategy count and low-medium trading frequency.

### 9) Main technical risks
- Runtime coupling leading to cascading failures.
- Monolith growth reducing maintainability.
- Latency spikes from mixed workloads (research + live).

---

## Version B — Scalable event-driven architecture

### 1) High-level design
A **service-oriented, event-driven platform**:
- Kafka/Redpanda (event bus)
- Independent services for market data, strategy, risk, OMS, portfolio, analytics
- Stateless compute services + state in DB/cache
- Replayable event logs for audit and simulation

### 2) Folder structure
```text
quant-platform/
  infra/
    docker/
    k8s/
    terraform/
  services/
    gateway-api/
    market-data-service/
    strategy-service/
    portfolio-service/
    risk-service/
    oms-service/
    execution-service/
    option-analytics-service/
    backtest-service/
    research-service/
    reporting-service/
    monitoring-service/
  libs/
    contracts/               # shared schemas (pydantic/avro/protobuf)
    broker-sdk/
    data-sdk/
    market-models/
    risk-rules/
  ops/
    runbooks/
    alert-policies/
```

### 3) Core modules
- **Event contracts**: `MarketDataEvent`, `SignalEvent`, `RiskDecisionEvent`, `OrderEvent`, `FillEvent`, `PnLEvent`.
- **Broker gateway services** per broker.
- **Market data normalizer service** with symbol master and US/HK calendar normalization.
- **Option analytics service** computing real-time greeks/IV/surfaces.
- **Stateful portfolio service** with snapshot + event sourcing.
- **Risk service** enforcing global/symbol/account limits.

### 4) Data flow
1. Market data ingested -> normalized -> published to topic(s).
2. Strategy service consumes and emits signals.
3. Portfolio service translates signals to intents.
4. Risk service approves/rejects intents.
5. OMS service places/manages orders via execution service.
6. Broker fills/events return through execution -> OMS -> portfolio.
7. Reporting/monitoring consume all events asynchronously.

### 5) How options are modeled
- Canonical option contract schema in shared `contracts` library.
- Chain snapshots and incremental updates on separate topics.
- Greeks and IV computed as streaming operators and persisted.
- Vol surface service materializes per-underlying surfaces and publishes derived metrics.

### 6) Pros
- High scalability and fault isolation.
- Strong observability and replay for post-mortems.
- Team-friendly parallel development.

### 7) Cons
- Significant operational complexity.
- Requires disciplined schema/version management.
- Higher cloud and maintenance cost.

### 8) Best use case
Growing operation with multiple strategies, higher throughput, and need for robust service separation.

### 9) Main technical risks
- Event ordering/idempotency mistakes.
- Schema drift across services.
- Increased operational overhead for a solo builder.

---

## Version C — Research-first architecture (backtesting + options analytics optimized)

### 1) High-level design
A **data-and-research centric architecture**:
- Central historical data lake + feature store
- Offline compute stack (batch/parallel) for walk-forward and parameter sweeps
- Thin live-trading runtime reusing validated models/strategies

### 2) Folder structure
```text
quant-platform/
  data/
    raw/
    normalized/
    features/
    options_surfaces/
  research/
    notebooks/
    factors/
    signals/
    experiments/
    walk_forward/
    performance_reports/
  engines/
    backtest/
    simulation/
    option_pricing/
  runtime/
    live/
    paper/
    shared_strategy_runtime/
  metadata/
    dataset_registry/
    model_registry/
    experiment_tracking/
  infra/
    docker/
    cloud/
```

### 3) Core modules
- **Data ingestion pipelines** for US/HK equities + options chains.
- **Feature factory** (factor computation, labeling, regime features).
- **Backtest engine** with realistic execution, fees, borrow, slippage.
- **Options analytics engine** for IV fitting, surface construction, greek scenario analysis.
- **Walk-forward orchestrator** with train/validate/test windows.
- **Report generator** (tear sheets, exposure, attribution, stability).

### 4) Data flow
1. Batch ingest historical market/options/reference data.
2. Normalize and store partitioned datasets.
3. Build factors/signals and options features.
4. Execute walk-forward backtests with parameter grids.
5. Persist experiment metrics and produce ranked candidates.
6. Promote selected strategy artifact to paper/live runtime.

### 5) How options are modeled
- Point-in-time chain store preserving listing/delisting and contract metadata.
- Surface builder with arbitrage checks (calendar/butterfly violations).
- Scenario greeks generated across spot/vol/time shocks.
- Strategy API can consume chain-level tensors or filtered contract universe.

### 6) Pros
- Strong research reproducibility and model governance.
- Superior options analytics depth.
- Clear handoff from research to runtime.

### 7) Cons
- Live trading path can be less mature initially.
- Heavy data engineering needs.
- Costly storage/compute for chain history.

### 8) Best use case
Quant founder prioritizing alpha discovery, robust backtesting, and options-modeling edge before scaling execution.

### 9) Main technical risks
- Data leakage/survivorship bias in research pipeline.
- Mismatch between backtest assumptions and live fills.
- Slow iteration if pipelines become too heavy.

---

## Version D — Production-first architecture (reliability + risk control optimized)

### 1) High-level design
A **mission-critical trading platform** with strict controls:
- Active-passive deployment across regions/AZs
- Dedicated risk gateway in order path (hard block)
- Immutable audit logs and deterministic state reconstruction
- Operational SRE controls (SLOs, incident runbooks, automated failover)

### 2) Folder structure
```text
quant-platform/
  control-plane/
    config-service/
    secrets-integration/
    feature-flags/
    deployment-controller/
  trading-plane/
    market-data-ingestion/
    strategy-runtime/
    risk-gateway/
    oms-core/
    execution-gateway/
    portfolio-ledger/
  analytics-plane/
    option-analytics/
    pnl-attribution/
    reporting/
  resilience/
    failover/
    replay/
    disaster-recovery/
  security/
    iam/
    audit/
    key-management/
  observability/
    metrics/
    logs/
    traces/
    alerts/
```

### 3) Core modules
- **Risk gateway** (non-bypassable): notional/position/order-rate/venue checks.
- **Kill-switch controller**: manual + automatic triggers.
- **Stale-data guard**: market-data heartbeat and quote age constraints.
- **Portfolio ledger**: double-entry accounting and reconciliation.
- **Config + secrets control plane** with versioned rollouts.
- **Compliance/audit stream** for every decision and order transition.

### 4) Data flow
1. Market data enters with heartbeat validation.
2. Strategy emits intents with model/version metadata.
3. Risk gateway enforces pre-trade controls; rejects or forwards.
4. OMS handles routing, throttles, and execution policy.
5. Fills update ledger and near-real-time PnL.
6. Post-trade risk recomputes exposures; triggers alerts/kill switch when breached.
7. All events mirrored to immutable audit store.

### 5) How options are modeled
- Contract master synchronized with broker + exchange references.
- Real-time greek aggregation at position/portfolio/book level.
- Stress testing across vol surface shocks and jump scenarios.
- Margin-aware risk checks (SPAN/broker margin estimates where available).

### 6) Pros
- Highest safety and reliability.
- Strong control/audit posture.
- Better suited for larger capital and strict risk constraints.

### 7) Cons
- Most complex and expensive architecture.
- Slower initial build velocity.
- Heavy ops and governance overhead for a single developer.

### 8) Best use case
Capital-sensitive production trading where risk containment and uptime dominate speed.

### 9) Main technical risks
- Over-engineering before product-market fit.
- Operational burden outpacing team capacity.
- Integration complexity across reliability/security subsystems.

---

## Ranking table (for a solo founder building a serious but manageable system)

| Rank | Version | Why it ranks here for solo founder |
|---|---|---|
| 1 | **A — Solo Monolith** | Best balance of seriousness and manageability; fastest route to live while keeping clean boundaries for later decomposition. |
| 2 | **C — Research-First** | Excellent if alpha discovery/options edge is priority; manageable if live scope is initially narrow. |
| 3 | **D — Production-First** | Very strong controls, but likely too heavy early unless managing larger capital/risk constraints immediately. |
| 4 | **B — Event-Driven** | Technically powerful but operationally costly and complex for one person in early stages. |

---

## Final recommendation
For a solo founder, start with **Version A** but incorporate selective elements from C and D:
1. Build A as modular monolith with strict interfaces for broker/data/risk/OMS.
2. Add C-style research pipeline early (experiment tracking + walk-forward + options surface artifacts).
3. Add D-style hard safety controls from day one (kill switch, stale data, max loss/limits, order-rate caps).
4. Define event schemas now so future migration toward B is incremental, not a rewrite.

This path provides fast execution, robust research depth, and prudent safety without overwhelming operational complexity.

---

## Principal engineer review of the 4 architectures

### Scoring legend
- **1 = poor / high risk / weak fit**
- **10 = excellent / low risk / strong fit**
- For **implementation complexity**, a higher score means easier to implement for a solo founder.

### Scorecard by architecture

#### Version A — Solo Monolith

| Category | Score (1-10) | Rationale |
|---|---:|---|
| Implementation complexity | 9 | Single deployable with fewer moving parts; fastest for one person. |
| Maintainability | 7 | Good initially with modular boundaries, but can degrade if discipline slips. |
| Reliability | 6 | Adequate if hardened, but shared process failure can impact all components. |
| Ease of debugging | 9 | Local reproducibility and simpler tracing are strong advantages. |
| Speed of iteration | 10 | Minimal infra friction gives very fast change-test-deploy loops. |
| Suitability for US/HK equities | 8 | Calendar/currency/session abstraction can be implemented cleanly. |
| Suitability for options trading | 7 | Supports options well, but heavy chain/greeks workloads can strain one runtime. |
| Extensibility for future multi-broker support | 8 | Adapter pattern scales well if interfaces are strict from day one. |
| Production safety | 7 | Can be strong if hard gates (kill switch/risk) are enforced in a single order path. |
| Cost efficiency for a solo founder | 10 | Lowest cloud/ops cost profile. |

**Top 3 strengths**
1. Fastest build and iteration velocity.
2. Lowest operational burden and cost.
3. Straightforward debugging and incident triage.

**Top 3 weaknesses**
1. Single-process coupling can cause broad blast radius.
2. Harder to isolate CPU/memory-heavy options analytics from live execution.
3. Risk of “big ball of mud” over time without architecture discipline.

**Likely failure points in live trading**
- Event loop stalls when options chain calculations spike.
- Shared DB latency impacts both market-data ingest and OMS decisions.
- Missing guardrails around stale data checks under market open load.

**Over-engineered vs under-engineered**
- **Over-engineered risk**: adding distributed patterns (complex event buses) too early.
- **Under-engineered risk**: treating risk gates as optional modules rather than mandatory in order path.

---

#### Version B — Scalable Event-Driven

| Category | Score (1-10) | Rationale |
|---|---:|---|
| Implementation complexity | 4 | Service decomposition, contracts, and event semantics are heavy for solo execution. |
| Maintainability | 7 | Good at scale, but only with strong platform discipline and tooling maturity. |
| Reliability | 8 | Fault isolation and replayability improve resilience when implemented correctly. |
| Ease of debugging | 5 | Cross-service tracing and ordering/idempotency issues are harder to debug. |
| Speed of iteration | 5 | Multi-service test/release cycles slow solo iteration. |
| Suitability for US/HK equities | 8 | Strong fit for high-throughput multi-session ingestion and normalization. |
| Suitability for options trading | 8 | Dedicated analytics streams/services handle chain and greeks workloads well. |
| Extensibility for future multi-broker support | 9 | Excellent extension model via broker gateway services. |
| Production safety | 8 | Centralized risk/OMS services can enforce robust controls. |
| Cost efficiency for a solo founder | 4 | Infra, observability, and ops overhead are expensive. |

**Top 3 strengths**
1. Strong scalability and service-level fault isolation.
2. Clean extensibility for additional brokers and venues.
3. Replayable events improve audit and simulation capabilities.

**Top 3 weaknesses**
1. High complexity in contracts, idempotency, and ordering guarantees.
2. Slow iteration for one engineer.
3. Elevated infrastructure and maintenance cost.

**Likely failure points in live trading**
- Duplicate/late events causing double-order or stale-position states.
- Schema evolution mismatch between producer and consumer services.
- Backpressure and lag during high-volatility options bursts.

**Over-engineered vs under-engineered**
- **Over-engineered risk**: building full microservice mesh before strategy-market fit.
- **Under-engineered risk**: insufficient distributed tracing and contract testing.

---

#### Version C — Research-First

| Category | Score (1-10) | Rationale |
|---|---:|---|
| Implementation complexity | 7 | Easier than distributed production platform; harder than monolith due to data pipelines. |
| Maintainability | 8 | Strong modular separation between data, research, and runtime artifacts. |
| Reliability | 6 | Research stack reliability is good; live runtime often less hardened early. |
| Ease of debugging | 7 | Experiment tracking and reproducibility help, though data pipelines can be complex. |
| Speed of iteration | 8 | Fast for research iteration; moderate for live execution refinements. |
| Suitability for US/HK equities | 8 | Strong for cross-market historical normalization and factor workflows. |
| Suitability for options trading | 9 | Best fit for chain history, IV surfaces, and scenario greek analytics. |
| Extensibility for future multi-broker support | 7 | Good if runtime adapters are designed early; not primary focus by default. |
| Production safety | 6 | Needs explicit investment to bring live controls to production-grade. |
| Cost efficiency for a solo founder | 7 | Storage/compute costs rise with options history but still manageable with scope control. |

**Top 3 strengths**
1. Best-in-class research and backtesting depth.
2. Strong options analytics (IV/surface/greek workflows).
3. Reproducible experiments and walk-forward governance.

**Top 3 weaknesses**
1. Potentially weaker operational hardening for live trading.
2. Data engineering overhead for quality historical options datasets.
3. Risk of delayed live deployment due to research-first bias.

**Likely failure points in live trading**
- Strategy behavior drift from backtest assumptions (latency/slippage/fill model gap).
- Insufficient real-time risk gating inherited from research runtime.
- Chain freshness issues when transitioning from batch to streaming inputs.

**Over-engineered vs under-engineered**
- **Over-engineered risk**: excessive offline experimentation frameworks before live feedback loop exists.
- **Under-engineered risk**: OMS/risk controls not hardened to match research sophistication.

---

#### Version D — Production-First

| Category | Score (1-10) | Rationale |
|---|---:|---|
| Implementation complexity | 3 | Very hard for solo founder: resilience, governance, and control-plane investment is large. |
| Maintainability | 6 | Strong process discipline required; complexity taxes long-term solo ownership. |
| Reliability | 9 | Highest reliability potential with failover, immutable audit, and strict control gates. |
| Ease of debugging | 4 | Multi-plane, high-control systems are difficult to reason about quickly. |
| Speed of iteration | 4 | Heavy process and controls slow strategy iteration cycles. |
| Suitability for US/HK equities | 8 | Very capable once built due to robust session/risk/ledger controls. |
| Suitability for options trading | 8 | Strong portfolio greek aggregation and stress/risk controls. |
| Extensibility for future multi-broker support | 8 | Good with standardized gateways and policy-driven controls. |
| Production safety | 10 | Best-in-class for kill-switches, hard risk limits, and auditability. |
| Cost efficiency for a solo founder | 3 | Highest engineering and operating cost burden. |

**Top 3 strengths**
1. Strongest risk containment and operational safety posture.
2. Superior audit/compliance and deterministic reconstruction.
3. High resilience through explicit failover and control planes.

**Top 3 weaknesses**
1. Slowest delivery and iteration for one builder.
2. Highest operational and governance overhead.
3. Significant risk of early-stage over-engineering.

**Likely failure points in live trading**
- Deployment/configuration errors across multiple control layers.
- Alert fatigue or misconfigured guard thresholds causing false trading halts.
- Operational toil consuming bandwidth needed for strategy improvements.

**Over-engineered vs under-engineered**
- **Over-engineered risk**: full enterprise reliability stack before stable revenue/alpha.
- **Under-engineered risk**: strategy research throughput can become secondary and stagnate.

---

## Final ranked comparison (solo founder criteria)

Criteria emphasized:
- fast build speed
- real backtesting capability
- eventual live deployment
- strong risk controls
- stocks + options support

| Final Rank | Version | Why |
|---|---|---|
| 1 | **Version A (with selective C + D upgrades)** | Best balance of build speed, manageable complexity, and practical route to live. Add walk-forward/options analytics (C) plus hard risk gates (D) early. |
| 2 | **Version C** | Best research and options edge; excellent backtesting. Slightly weaker out-of-the-box live reliability unless you deliberately add production controls. |
| 3 | **Version D** | Safest and most robust operationally, but too heavy for most solo founders at initial stage. |
| 4 | **Version B** | Highly scalable and extensible, but complexity/cost/debug burden generally misaligned with solo execution in early phases. |

## Winner and justification
**Winner: Version A, intentionally upgraded with targeted elements from Version C and Version D.**

Why this wins for the stated goals:
1. **Fast build speed**: Version A has the shortest time-to-first-strategy and lowest infra burden.
2. **Real backtesting**: Add C-style walk-forward, experiment tracking, and realistic execution modeling immediately.
3. **Eventual live deployment**: Keep strict module interfaces (broker/data/risk/OMS) so decomposition is incremental later.
4. **Strong risk controls**: Import D-style hard risk gateway semantics into the monolith order path from day one.
5. **Stocks + options**: Prioritize robust option chain/greek/surface modules and isolate heavy analytics into background workers.

Practical implementation sequence:
- **Phase 1**: Version A core (broker/data abstraction, strategy, OMS, portfolio, risk gates, backtest).
- **Phase 2**: Version C research depth (factor pipeline, walk-forward orchestration, options surface store).
- **Phase 3**: Version D safety hardening (non-bypassable risk checks, kill-switch automation, strict stale-data guards, reconciliation).
- **Phase 4**: Selective Version B extraction only where load demands it (e.g., market-data ingest or option analytics service).

---

## Final combined architecture (A + C hybrid, with D-grade safety controls)

This final architecture combines:
- **Version A strengths**: simple modular monolith, fast solo iteration, low ops overhead.
- **Version C strengths**: strong research/backtesting workflow and options analytics depth.
- **Version D safety subset**: non-bypassable risk gates, kill switch, stale-data guards, and strict operational controls.

Design principle: **single deployable runtime with strict internal boundaries**, plus **separate asynchronous workers** for heavy research/options analytics tasks.

### 1) Project tree
```text
quant-trader/
  pyproject.toml
  docker-compose.yml
  .env.example
  configs/
    base.yaml
    env/
      dev.yaml
      paper.yaml
      live.yaml
    risk_limits.yaml
    brokers.yaml
  src/
    app/
      main.py                       # runtime entrypoint
      modes.py                      # backtest/paper/live mode selection
      wiring.py                     # dependency injection and startup graph

      core/
        clock.py
        scheduler.py
        event_bus.py                # internal async event bus
        idempotency.py

      interfaces/
        broker.py                   # BrokerGateway protocol
        market_data.py              # MarketDataGateway protocol
        risk.py                     # RiskEngine protocol
        storage.py                  # Repository protocol
        pricing.py                  # OptionPricing protocol

      market/
        instruments.py
        calendars.py                # US/HK sessions + holidays
        symbology.py                # mapping internal/broker/vendor symbols
        fx.py                       # USD/HKD conversion and rates snapshots

      data/
        ingest/
          stream_runner.py
          bar_builder.py
          chain_collector.py
        normalization/
          quote_normalizer.py
          chain_normalizer.py
        quality/
          stale_guard.py
          sanity_checks.py

      strategy/
        base.py
        signal_engine.py
        universe.py
        stock_strategies/
        option_strategies/

      portfolio/
        targets.py
        positions.py
        pnl.py
        exposures.py
        ledger.py

      risk/
        pre_trade.py                # hard checks before OMS
        post_trade.py               # ongoing exposure and drawdown checks
        limits.py                   # max loss, position, order-rate, notional
        kill_switch.py

      oms/
        order_intent.py
        order_state_machine.py
        router.py
        execution_policy.py

      execution/
        paper_executor.py
        live_executor.py
        broker_adapters/
          ibkr.py
          alpaca.py

      options/
        chain_store.py
        greeks_engine.py
        iv_engine.py
        vol_surface.py
        scenario_risk.py

      research/
        datasets.py
        factors.py
        signal_lab.py
        walk_forward.py
        reports.py

      backtest/
        engine.py
        market_replay.py
        fill_model.py
        cost_model.py
        validation.py

      storage/
        models.py
        repositories.py
        migrations/

      observability/
        logging.py
        metrics.py
        tracing.py
        alerts.py

      security/
        secrets.py

  workers/
    option_analytics_worker.py      # async heavy computations
    report_worker.py

  scripts/
    run_backtest.py
    run_paper.py
    run_live.py
    reconcile_positions.py

  tests/
    unit/
    integration/
    regression/
```

### 2) Module responsibilities
- **interfaces/**: stable contracts to decouple business logic from vendors.
- **data/**: collect and normalize US/HK market and option-chain data with freshness checks.
- **strategy/**: generate signals from normalized events and defined universe.
- **portfolio/**: convert signals to target positions, manage PnL/exposures and accounting ledger.
- **risk/**: enforce non-bypassable controls (pre-trade + post-trade) and trigger kill switch.
- **oms/**: transform intents into executable orders and track lifecycle.
- **execution/**: route paper/live orders via broker adapters.
- **options/**: compute greeks, implied vol, and surfaces for strategy + risk.
- **research/** + **backtest/**: reproducible factor research, walk-forward tests, and performance reports.
- **observability/**: logs/metrics/alerts for health and trading safety.

### 3) Interface boundaries
Keep boundaries explicit and testable:
- `StrategyEngine` -> emits `Signal` only (never talks directly to broker).
- `PortfolioService` -> translates `Signal` to `OrderIntent`.
- `RiskEngine` -> must approve intent before OMS; reject reason is mandatory.
- `OMS` -> owns order state machine and broker routing decisions.
- `BrokerGateway` -> only module allowed to call external broker APIs.
- `MarketDataGateway` -> only module allowed to call external data APIs.
- `OptionPricing` -> pure analytics interface for greeks/IV/surface with deterministic inputs.

This keeps the system modular while retaining monolith simplicity.

### 4) Data model definitions
Core entities (Pydantic/dataclass/ORM):
- **Instrument**
  - `instrument_id`, `asset_class` (`EQUITY`, `OPTION`), `symbol`, `exchange`, `currency`
  - Option fields: `underlying_id`, `expiry`, `strike`, `right` (`CALL`/`PUT`), `multiplier`
- **QuoteBar**
  - `instrument_id`, `ts`, `open`, `high`, `low`, `close`, `volume`, `vwap`, `source`
- **OptionQuote**
  - `instrument_id`, `ts`, `bid`, `ask`, `last`, `mid`, `bid_size`, `ask_size`
- **OptionGreekSnapshot**
  - `instrument_id`, `ts`, `iv`, `delta`, `gamma`, `vega`, `theta`, `rho`, `model`, `inputs_hash`
- **VolSurfacePoint**
  - `underlying_id`, `ts`, `expiry`, `moneyness_or_delta`, `iv`, `quality_flag`
- **Signal**
  - `strategy_id`, `instrument_id`, `ts`, `direction`, `strength`, `horizon`, `metadata`
- **OrderIntent**
  - `intent_id`, `strategy_id`, `instrument_id`, `side`, `qty`, `order_type`, `limit_price`, `time_in_force`
- **Order**
  - `order_id`, `intent_id`, `broker_order_id`, `status`, `filled_qty`, `avg_fill_price`
- **Fill**
  - `fill_id`, `order_id`, `ts`, `qty`, `price`, `fees`, `liquidity_flag`
- **PositionLot**
  - `lot_id`, `instrument_id`, `open_ts`, `qty_open`, `avg_open_price`, `strategy_id`
- **PnLSnapshot**
  - `account_id`, `ts`, `realized`, `unrealized`, `total`, `by_strategy`, `by_asset_class`
- **RiskSnapshot**
  - `ts`, `gross_exposure`, `net_exposure`, `delta`, `gamma`, `vega`, `drawdown`, `limit_breaches`

### 5) Event model definitions
Use an internal typed event bus (async queue + persisted outbox for replay-lite):
- `MarketDataEvent` (quote/bar/tick)
- `OptionChainEvent` (chain snapshot/increment)
- `SignalEvent`
- `TargetPositionEvent`
- `OrderIntentEvent`
- `RiskDecisionEvent` (`APPROVE`, `REJECT`, `HALT`)
- `OrderStateChangedEvent`
- `FillEvent`
- `PositionChangedEvent`
- `PnLUpdatedEvent`
- `RiskAlertEvent`
- `SystemHealthEvent`

Event requirements:
- immutable payload
- event id + correlation id + causation id
- idempotency key for all trading-critical actions
- timestamp from monotonic clock + exchange timestamp when available

### 6) Order lifecycle model
`DRAFT_INTENT -> RISK_PENDING -> APPROVED -> ROUTED -> ACKNOWLEDGED -> PARTIALLY_FILLED -> FILLED`

Failure/terminal branches:
- `REJECTED_RISK`
- `REJECTED_BROKER`
- `CANCEL_PENDING -> CANCELED`
- `EXPIRED`
- `HALTED_BY_KILL_SWITCH`

Rules:
- no transition to `ROUTED` without explicit risk approval.
- partial fills update position and residual quantity immediately.
- cancel/replace is versioned to avoid order-state ambiguity.

### 7) Position lifecycle model
`FLAT -> OPENING -> OPEN -> SCALING -> REDUCING -> CLOSED`

Lifecycle behavior:
- position lots are lot-tracked for realized PnL accuracy.
- every fill mutates position atomically with ledger update.
- corporate actions and contract expiry events trigger position transforms.
- option expiry assignment/exercise paths handled as explicit lifecycle events.

### 8) Option analytics pipeline
Two-speed pipeline:
1. **Real-time lightweight path (in runtime)**
   - compute near-the-money greeks + IV for tradable universe.
   - enforce stale-chain and stale-underlying checks before trading.
2. **Asynchronous heavy path (worker)**
   - full surface fitting by tenor/strike or tenor/delta.
   - arbitrage sanity checks (calendar/butterfly flags).
   - scenario shocks for portfolio greek stress.

Outputs feed:
- strategy features
- risk aggregation (`delta/gamma/vega` caps)
- reporting dashboards

### 9) Backtesting workflow
1. Load point-in-time instruments and historical US/HK data + options chains.
2. Replay market events through same strategy/portfolio/risk/OMS interfaces.
3. Apply realistic fill/cost/slippage models and market session calendars.
4. Generate positions, PnL, and risk snapshots.
5. Run walk-forward validation across rolling windows.
6. Produce standardized performance/risk reports and promote eligible configs.

Backtest/live parity rule: strategy and risk logic must be shared code, not reimplemented.

### 10) Live trading workflow
1. Start session scheduler (US/HK calendars).
2. Ingest live market and option-chain data with heartbeat monitoring.
3. Strategy emits signals -> portfolio creates intents.
4. Pre-trade risk enforces limits and stale-data guards.
5. OMS routes approved orders to broker adapter.
6. Fills update positions/PnL/ledger in near real-time.
7. Post-trade risk recomputes drawdown/exposure and can trigger kill switch.
8. End-of-day reconciliation compares broker positions/orders with internal ledger.

### 11) Monitoring and alerting workflow
- **Logs**: structured JSON logs with strategy/account/order correlation ids.
- **Metrics**:
  - market data freshness lag
  - order ack latency
  - fill ratio/slippage
  - risk limit utilization
  - strategy PnL and drawdown
- **Alerts**:
  - stale data threshold breach
  - repeated order rejects
  - risk limit breach
  - reconciliation mismatch
  - heartbeat loss from broker/data providers
- **Escalation**:
  - alert -> automated protective action (throttle/halt) -> human notification.

### 12) Deployment approach
- **Local dev**: single process + Postgres + Redis via docker-compose.
- **Docker prod-lite**: one main app container + optional worker containers.
- **Cloud-ready**:
  - deploy main runtime and workers separately (ECS/Kubernetes/VMs).
  - managed Postgres + secret manager + monitoring stack.
  - blue/green deploy for runtime updates outside market hours when possible.

Keep infra minimal initially; add managed components before adopting microservices.

### What to build first (must-have v1)
1. Instrument and market data normalization (US/HK equities + options contracts).
2. Broker abstraction with one primary broker + paper executor.
3. Shared strategy/portfolio/risk/OMS/backtest interfaces.
4. Non-bypassable pre-trade risk checks (max loss, position limits, order-rate limits, stale data guard).
5. Deterministic order/position state machines + PnL tracking.
6. Minimal monitoring: structured logs, core metrics, critical alerts.

### What can be postponed
- Multi-broker live failover and smart routing.
- Full distributed event bus and service decomposition.
- Advanced vol models beyond robust baseline IV/surface interpolation.
- Multi-region active-passive failover.
- Rich UI dashboards (start with reports + alerts).

### What should never be skipped for safety
- Hard kill switch (manual + automatic).
- Pre-trade and post-trade risk gates enforced in the order path.
- Stale market-data protection and heartbeat checks.
- Idempotent order submission/cancel handling.
- End-of-day reconciliation and discrepancy alerts.
- Secrets management hygiene and audit-grade order/risk logs.

---

## Implementation progress update

### Phase 3 (implemented): Broker abstraction and OMS safety core
- Added broker abstraction with submit/cancel/replace/get order/poll fills/list positions paths.
- Added execution service layer to isolate OMS from broker adapter details.
- Added order lifecycle state machine validation.
- Added fill processing with partial/full fill handling and duplicate event protection.
- Added position updater for fill-driven inventory and average cost updates.
- Added concrete risk manager with:
  - pre-trade checks
  - max position size
  - max order notional
  - daily loss guard
  - rate limit guard
  - duplicate order prevention (idempotency key in OMS)
  - stale quote protection
  - emergency kill switch

### Phase 4 (implemented): Strategy engine framework
- Added modular `BaseStrategy` foundation with support for both event-driven and scheduled execution paths.
- Added strategy-domain models for alpha signals and portfolio targets, explicitly separated from OMS execution objects.
- Added `StrategyEngine` orchestration that can run strategies uniformly in backtest/paper/live through runtime context.
- Added portfolio-construction bridge from signal outputs to target outputs and optional execution handoff integration point.
- Added educational example strategies:
  - US equity momentum
  - HK equity mean reversion
  - Covered call options strategy
  - Options volatility breakout strategy

### Phase 5 (implemented): Event-driven backtesting framework
- Added event-driven backtest engine with chronological bar replay and next-bar execution semantics.
- Added configurable slippage and commission/fee models.
- Added portfolio accounting with cash ledger, position tracking, realized/unrealized PnL, and drawdown snapshots.
- Added PnL attribution by instrument and asset class, plus benchmark comparison and performance report generation.
- Added options contract handling with expiration processing and assignment/exercise hook interface.
- Added explicit assumptions and limitations output to avoid unsupported survivorship-bias claims.

### Phase 6 (implemented): Production-focused risk framework
- Added instrument-level controls (max position per instrument).
- Added portfolio-level controls (sector/group exposure, gross/net exposure, daily loss, strategy drawdown).
- Added market-level guard for stale quote detection.
- Added options-specific controls for greek limits and expiration risk thresholds.
- Added operational controls for broker connectivity health, max order-rate, duplicate order prevention, and emergency stop workflow.
- Added risk audit logging for allow/block decisions.

### Phase 7 (implemented): Deployment and operations readiness
- Added containerization artifacts (`Dockerfile`, `docker-compose.yml`) for local and cloud-ready deployment workflows.
- Added environment management (`.env.example`) and developer command automation (`Makefile`).
- Added health checking components and scripts for readiness/liveness integration.
- Added scheduler setup components and runnable scheduler process script.
- Added monitoring and alerting integration hooks for future observability stack integration.
- Added database migration runner and SQL migration directory approach.
- Added operational runbook with incident response and emergency stop workflow.
