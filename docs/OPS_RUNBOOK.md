# QuantTrader Operational Runbook (Phase 7)

## 1. Local developer bootstrap
1. Copy `.env.example` to `.env` and adjust values.
2. Run `make setup`.
3. Run migrations: `make migrate`.
4. Start app: `make run`.
5. Run health check: `make health`.

## 2. Docker local stack
1. Ensure Docker/Compose is installed.
2. Copy `.env.example` to `.env`.
3. Start stack: `make docker-up`.
4. Verify health:
   - `docker compose ps`
   - app health check should report `healthy`.
5. Stop stack: `make docker-down`.

## 3. Cloud-ready deployment pattern
- Build image: `make docker-build`.
- Push image to registry (ECR/GCR/ACR).
- Deploy app and scheduler as separate services.
- Attach managed database and secret manager.
- Run migration job before app rollout.
- Use readiness probe via `scripts/healthcheck.py` equivalent.

## 4. Health and monitoring hooks
- Health checker evaluates DB, broker connectivity, and market data freshness.
- Scheduler emits heartbeat logs for orchestration visibility.
- Monitoring hooks (`MetricsSink`) are integration points for Prometheus/StatsD/OTel.
- Alerting hooks (`LoggingAlertSink`) are integration points for PagerDuty/Slack/webhooks.

## 5. Incident response
### Emergency stop path
1. Trigger risk emergency stop in orchestration layer.
2. Verify no new orders are accepted.
3. Confirm kill-switch reason in logs/audit trails.
4. Reconcile positions and open orders.
5. Clear emergency stop only after root-cause mitigation.

### Broker connectivity incident
1. Health check should fail broker component.
2. Halt order submissions.
3. Continue monitoring fills/order status until broker recovers.
4. Reconcile broker state after recovery.

### Stale market data incident
1. Confirm stale-feed alert firing.
2. Block strategy order generation for affected symbols.
3. Switch to backup feed if available.
4. Resume trading only after fresh data consistency checks.

## 6. Database migration operations
- Migrations are SQL files in `db/migrations`.
- Run with `python scripts/migrate.py`.
- Each migration is tracked in `schema_migrations`.
- Never edit applied migration files; add new versioned file instead.

## 7. Audit and logging
- Use JSON structured logging (`QT_LOG_JSON_LOGS=true`) in non-local environments.
- Risk framework stores allow/block audit records for pre-trade decisions.
- Include deployment metadata (version/environment) in process logs via environment variables.
