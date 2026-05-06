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
