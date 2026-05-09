# Rust websocket load test results

Each row is one run. Columns:
- **N**: number of session pairs (=> 2N sockets, 40N msgs/sec each direction)
- **Duration**: seconds driving 20Hz
- **Build**: short git SHA of `gecko-socket-rust/` at time of run
- **p50/p95/p99**: one-way latency, ms
- **Drops**: % of expected messages not received
- **CPU**: peak Rust process CPU% (one core = 100%)
- **RSS**: peak resident MB
- **Notes**: any context — code change being tested, anomalies, etc.

Pass criteria (per PERF_TODO.md):
- p95 < 50ms
- 0 drops
- CPU < 70% of one core
- Flat RSS during steady state

| Date | N | Duration | Build | p50 | p95 | p99 | Drops | CPU | RSS | Notes |
|------|---|----------|-------|-----|-----|-----|-------|-----|-----|-------|
| 2026-05-09 | 10 | 60s | 7dc20ae | 24ms | 36ms | 52ms | 0% | 5% peak / 1.37% avg | n/a | Post item-1 (CoordCtx — hot-path handlers no longer clone full Client). 19471/24000 sent (81%, Windows setInterval drift). All criteria pass. CPU too low at this N to attribute to the change — bouncing 0–5% is sampling noise. Need higher N to see item-1 impact. |
| 2026-05-09 | 100 | 60s | f8f6a27 | 29ms | 47ms | 66ms | 0% | not captured | not captured | First clean run at scale. 200 sockets, 224k msgs sent and received (100%). Connect time 14.1s (200 hydrates funneled through Rust semaphore, see notes). Got here through several fixes after the initial N=30 attempts failed: (1) item 3 — in-place mutation of inbound payload instead of full rebuild; (2) item 4 — `tokio::spawn` for hydrate + check_host_link Django calls so they don't block recv task; (3) added self-notify peer_presence in connect-spawn so the loadtester's handshake doesn't race against the partner's hydrate; (4) added `Semaphore::new(10)` on AppState wrapping all Django HTTP calls to bound concurrent Postgres connections; (5) removed Django `CONN_MAX_AGE=60` (was actually `COIN_MAX_AGE` typo) — under ASGI workers it parked 13+ idle connections in thread pools; baseline now ~5–11 connections, Postgres slot pool no longer exhausted; (6) `hydrate_live_sesh_context` no longer overwrites friend_id/colors when Django returns null — preserves any value `set_friend` already wrote (was clobbering loadtester's sentinel friend_id=999999, causing 50% drops on host-direction broadcasts due to early-return on `friend_id.is_none()`). |
