# Rust Websocket Performance TODO

Ranked from biggest expected win to smallest. File of interest: `src/main.rs`.

---

## 1. Bound the per-client send channel
**Current:** `mpsc::unbounded_channel::<Message>()` (line ~1591). A slow/dead client can balloon memory because nothing back-pressures the producer.
**Fix:** switch to `mpsc::channel(256)` (or similar). On `try_send` failure, drop the message or force-disconnect the client.
**Why biggest:** single largest reliability + memory-stability improvement under load. One stuck mobile client today can OOM the server.

---

## 2. Kill the write-lock on `mark_seen` (hot-path lock contention)
**Current:** every inbound text/binary/ping frame calls `mark_seen` → `clients.write().await` just to update `Instant`. This blocks all concurrent reads and broadcasts.
**Options (pick one):**
- Remove `last_seen` entirely — nothing reads it.
- Store as `Arc<AtomicU64>` (millis) inside `Client` so updates need only a read lock.
- Replace `RwLock<HashMap<...>>` with `dashmap::DashMap` for sharded concurrency.
**Why high:** this lock is taken on *every* inbound coord packet, currently serializing the whole server.

---

## 3. Add Django-call timeouts + connection pool tuning
**Current:** `reqwest::Client::new()` (line ~1537) — all defaults, no timeout. `proxy_action_to_django` and `hydrate_live_sesh_context` can stall the per-connection task indefinitely if Django hiccups.
**Fix:**
```rust
reqwest::Client::builder()
    .timeout(Duration::from_secs(5))
    .connect_timeout(Duration::from_secs(2))
    .pool_max_idle_per_host(32)
    .build()
```
**Why high:** prevents one slow Django response from cascading into stuck websockets.

---

## 4. Stop cloning room member sets on every broadcast
**Current:** `broadcast_to_room` does `rooms.get(room_name).cloned()` — clones the whole `HashSet<ClientId>` per send.
**Fix options:**
- Store `Arc<HashSet<ClientId>>` in the rooms map so the clone is a refcount bump.
- Or hold the `rooms.read()` guard for the duration of the broadcast loop (simpler, but extends lock hold time — only do this if rooms are small).
**Why mid:** matters most for high-frequency coord streams (`gecko_coords`, `host_gecko_coords`, etc.) into populated rooms.

---

## 5. Add an idle-connection reaper
**Current:** `last_seen` is updated but never read. Half-open TCP sockets accumulate forever.
**Fix:** spawn a periodic task (e.g. every 30s) that scans clients and closes any whose `last_seen` is older than N seconds. Pair with WS ping frames if not already enforced.
**Why mid:** prevents long-tail resource leak; only matters at scale or over long uptime.

---

## 6. Replace `println!` with `tracing`
**Current:** `println!` everywhere — synchronous stdout writes under load become a bottleneck and have no levels/structure.
**Fix:** add `tracing` + `tracing-subscriber` with a non-blocking writer; use `info!`, `warn!`, `error!`.
**Why lower:** mostly observability + small throughput win; no behavioral change.

---

## 7. Verify cheap-clone for outbound messages
**Current:** `broadcast_to_room` encodes once and clones the `Message` per recipient. `Message::Binary` wraps `Bytes` (refcount clone — good). `Message::Text` wraps `Utf8Bytes` — confirm this is also a cheap clone in the axum 0.7 version pinned.
**Action:** sanity-check; if `Text` is a deep clone, pre-encode JSON to `Bytes` and send as a shared buffer.
**Why lower:** likely already correct; just worth confirming.

---

## 8. (Future / only if needed) Multi-node fanout layer
**Current:** single-process, in-memory rooms. Faster than Redis for one node.
**When this matters:** the day we want >1 Rust node behind a load balancer. Then add Redis pub/sub or NATS as a cross-node broadcast bus for rooms + user lookups.
**Why last:** premature today; the in-memory design is correct for a single instance.

---

## Notes / out of scope
- Models and migrations stay hands-off — Taylor handles those personally.
- None of the above changes the wire protocol, so the React Native client needs no updates.

---

# Load testing & long-term capacity validation

The headline question we want to answer: **how many concurrent 2-user sessions can the Rust server sustain at 20Hz for 60 seconds without latency degradation?** This was the main motivation for migrating off the Django Channels consumer (old setup capped out at a handful of simultaneous sessions).

## Definition of a "session" for testing
- 2 connections, paired via a `LiveSesh` row in Django, both end up in the same `gecko_shared_with_friend_X` room after `hydrate_live_sesh_context`.
- One side sends `update_host_gecko_position` at 20Hz, the other sends `update_guest_gecko_position` at 20Hz.
- Each inbound packet broadcasts to exactly 1 other client in the room.
- N sessions = 2N connections, 40N inbound msgs/sec, 40N outbound msgs/sec.

## "Without degrading" — concrete pass/fail criteria
- Latency p95 (sender `send()` → receiver `onmessage`) stays under **50ms**.
- Zero dropped messages over the 60-second window.
- Rust CPU stays under ~70% of one core.
- RSS grows linearly with N during ramp-up, then flat during steady state (no leak).

## Setup needed (one-time)

### 1. Django management command (Taylor implements)
Provisions test data and emits a JSON file the load tester consumes.
- Creates N pairs of test users (`loadtest_user_001` … `loadtest_user_2N`).
- Creates N `LiveSesh` rows pairing them, one host + one guest per pair.
- Mints 2N short-lived gecko-socket JWTs by reusing the logic from the `gecko_socket_token` view (no HTTP round-trips during the load test).
- Writes `loadtest_users.json`:
  ```json
  [
    { "host_token": "...", "guest_token": "..." },
    ...
  ]
  ```
- Should also support a `--cleanup` flag to delete the test users + sessions afterward, since they'll otherwise pollute prod data.

### 2. Node load tester (lives in `gecko-socket-rust/loadtest/` on the laptop, NOT on the droplet)
- Reads `loadtest_users.json`.
- Opens 2N WebSockets to `wss://badrainbowz.com/ws/gecko-rust-test/` with `Sec-WebSocket-Protocol: gecko.v1, jwt.<token>`.
- Waits for `peer_presence: online` on both sides of each pair.
- Drives 20Hz position updates for 60s, with `timestamp: Date.now()` baked into each payload.
- On received messages, computes one-way latency from baked timestamp → arrival time, logs to `latencies.csv`.
- Prints summary at end: msgs sent/received per side, drop count, p50/p95/p99 latency, total bytes.
- Why on the laptop and not the droplet: the droplet *is* the system under test; co-locating the load generator skews the numbers and competes for CPU.

## Test sequence
1. Start with N = 50 sessions for 60s — establishes baseline.
2. Scale up: N = 100, 250, 500, 1000 (or until something breaks).
3. Record per run: msgs/sec, p95 latency, CPU%, RSS MB. Save as a markdown table per change to `gecko-socket-rust/loadtest/results.md`.
4. The breakpoint (where latency cliff appears or drops start) is the current capacity number.

## How this integrates with the perf TODO above
The point of items 1–7 of the perf TODO is to push the breakpoint higher. Run the load test once for a baseline, then re-run after each change. The before/after numbers go in the same `results.md` table — that's the proof each change actually mattered.

## Long-term: testing once we have real users
Synthetic load tests stop being safe to run against prod once real users are on the system. Progression:

- **Phase 1 (now, no users):** synthetic load tests as described above. Free to degrade prod since it's just us.
- **Phase 2 (small user count):** keep load tester for big architectural changes; for day-to-day rely on **passive metrics** — in-process counters (`msgs_in`, `broadcasts_out`, `clients_connected`) printed every 10s to journalctl, plus DigitalOcean's CPU/RAM graphs. Run synthetic tests at off-peak hours (3 AM) and announce the test window so user-reported issues during it can be correlated.
- **Phase 3 (production at scale):** shadow traffic to a staging Rust instance, canary deploys behind a load balancer, Prometheus/Grafana for histograms (p50 lies; p99 is what real users feel). Don't build phase 3 until phase 2 metrics start lying to us.

## Comparison vs. the old Channels consumer
- Honest apples-to-apples requires resurrecting the old consumer on a separate droplet/port and running the same load test against both. A few hours of git-archaeology work; only worth doing once if we want a real comparison.
- Cheaper proxy: pick a workload the old setup couldn't handle (e.g. "5 simultaneous sessions at 20Hz lagged"), confirm the Rust setup handles 10× that cleanly. That's enough to validate the migration was worth it without resurrecting anything.
- Metrics that translate across stacks: connections, bytes/sec, broadcast latency. Metrics that don't: Redis pubsub rate, gunicorn worker count, Channels-specific counters.
