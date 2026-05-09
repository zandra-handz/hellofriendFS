# RESCUING RUST HOTPATH

Cleanup pass on `gecko-socket-rust/src/main.rs` to free CPU on the 1 vCPU droplet. Hot path = the gecko-coord broadcasts that fire many times per second per session: `update_gecko_position`, `update_host_gecko_position`, `update_guest_gecko_position`, `update_capsule_progress`, plus `broadcast_to_room` itself.

Work the list top-to-bottom. Each item is a self-contained change.

---

## 0. Switch `println!` -> `tracing` with non-blocking writer
**Status:** done.

`tracing` + `tracing_appender::non_blocking` is wired in `main`. All call sites use `info!` / `warn!` / `error!` / `debug!`. The peer-presence and hydrate logs are now `debug!` so they're off by default in prod (set `RUST_LOG=info` or higher).

---

## 1. Stop cloning the whole `Client` on every coord update
**Where:** `get_client()` at main.rs:1321, called from every `handle_update_*` handler.

`get_client()` returns a fully-cloned `Client` — 8 `Option<String>`s + two `RoomName`s — when the hot-path callers only need `(user_id, friend_id, is_host, shared_room)`.

**Do:** add a small helper that returns just what the hot path needs while holding the read lock once. Something like:

```rust
struct CoordCtx {
    user_id: UserId,
    friend_id: Option<u64>,
    is_host: bool,
    shared_room: RoomName, // still one clone, unavoidable for broadcast
}

async fn coord_ctx(state: &AppState, client_id: &str) -> Option<CoordCtx> { ... }
```

Replace `get_client(...).await` in:
- `handle_update_gecko_position`
- `handle_update_host_gecko_position`
- `handle_update_guest_gecko_position`
- `handle_update_capsule_progress`
- `handle_send_all_host_capsules`

Leave `get_client` for the cold paths that genuinely need the full struct (`handle_join_live_sesh`, `handle_request_peer_presence`, `disconnect_cleanup`, etc.).

---

## 2. Collapse the two RwLock acquires per broadcast
**Where:** `broadcast_to_room` at main.rs:1333.

Per coord frame today: `get_client()` takes `clients.read()`, drops it. `broadcast_to_room` then takes `rooms.read()`, drops it, then `clients.read()` again. 3 lock ops/frame. On 1 vCPU under contention this adds up.

**Options, pick one:**

a) Inline the broadcast into the handlers and reuse one `clients.read()` guard across the room+clients lookup. The hot-path helper from item 1 can return inside an existing read guard.

b) Swap `Arc<RwLock<HashMap<...>>>` for `dashmap::DashMap` on `clients` and `rooms`. Per-shard locking, no global writers blocking readers. Drop-in-ish but touches every access site.

Recommend (a) first since it's smaller; reach for (b) if profiling still shows lock contention with hundreds of concurrent sessions.

---

## 3. Stop parse->rebuild->re-serialize on every coord frame
**Where:** `handle_update_host_gecko_position` (main.rs:832), and the same pattern in the guest/capsule variants.

Today: incoming msgpack -> `serde_json::Value` (`handle_incoming` line 312) -> handler does `payload.get("steps").cloned()` etc. for ~9 fields, building a brand-new `json!{...}` -> `rmp_serde::to_vec_named` re-serializes the rebuilt map.

**Do:** for pure relay actions, mutate the incoming `Value` in place — inject `from_user` / `friend_id` into the existing `data` object and forward it as-is. Skeleton:

```rust
let mut payload = data.unwrap_or_else(|| json!({}));
if let Value::Object(map) = &mut payload {
    map.insert("from_user".into(), json!(ctx.user_id));
    map.insert("friend_id".into(), json!(ctx.friend_id));
}
broadcast_to_room(state, &ctx.shared_room, Some(ctx.user_id),
    OutgoingMessage { action: "host_gecko_coords".into(), data: payload }).await;
```

Saves ~9 `Value::clone()`s and a fresh map allocation per frame. Biggest CPU win on the list, but the most invasive — do it after items 1 + 2 are merged so you can profile the delta.

Stretch goal: skip parsing inbound coord msgpack to `Value` entirely and forward the raw bytes with a small header tweak. Only worth it if profiling shows `rmp_serde::from_slice` is hot.

---

## 4. Don't await Django HTTP calls inline on the recv task
**Where:**
- `handle_join_live_sesh` at main.rs:495 awaits `hydrate_live_sesh_context` and then `proxy_check_host_link_and_load`.
- `handle_socket` at main.rs:258 awaits `hydrate_live_sesh_context` before the recv loop starts.

Every one of these blocks the websocket recv task on a Django round-trip (potentially seconds, since gunicorn/uvicorn workers contend for the same 1 vCPU). The connect path at line 265 already does the right thing with `tokio::spawn`.

**Do:** wrap both calls in `tokio::spawn` with a `state.clone()` + `client_id.clone()`. Send any resulting "ready" / "ok" frames from inside the spawned task via `send_to_client`, which already takes `&AppState`.

Caveat: if the client expects `join_live_sesh_ok` *before* `capsule_matches_ready`, preserve that ordering inside the spawned task — don't fan out into two parallel spawns.

---

## 5. Index clients by `user_id` to kill linear scans
**Where:**
- `evict_existing_user` at main.rs:1270 — runs on every connect.
- `internal_push_user` at main.rs:1411.
- `internal_disconnect_user` at main.rs:1507.
- The `partner` lookup in `handle_request_peer_presence` at main.rs:666 (`clients.values().find(|c| c.user_id == partner_id)`).

All four scan the full `clients` map. With N concurrent users it's O(N) per operation; eviction-on-connect makes total connect cost O(N).

**Do:** add a secondary index to `AppState`:

```rust
user_clients: Arc<RwLock<HashMap<UserId, HashSet<ClientId>>>>,
```

Maintain it in the same critical sections that mutate `clients` (insert in `handle_socket`, remove in `disconnect_cleanup`). Then the four call sites become O(1) lookups.

---

## Validation plan

After each item:
1. `cargo build --release` clean.
2. Run the loadtester (`loadtest/`) with the same scenario as the baseline; record CPU on the droplet (or local) and p50/p99 broadcast latency.
3. If a change doesn't show up in the numbers, revert and move on rather than carrying dead complexity.
