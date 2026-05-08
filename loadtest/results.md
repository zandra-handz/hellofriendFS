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
|      |   |          |       |     |     |     |       |     |     |       |
