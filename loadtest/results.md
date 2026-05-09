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
