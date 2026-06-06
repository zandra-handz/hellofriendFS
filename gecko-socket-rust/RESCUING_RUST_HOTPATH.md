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
**Status:** implemented (steps 1-9 in code, `cargo check` clean). Loadtest validation (step 10.2/10.3) still pending.

Several operations answer "which client(s) belong to user X?" by scanning the
*entire* `clients` map. With N concurrent users that's O(N) per operation, and
eviction-on-connect makes total connect cost O(N). The fix is a secondary index
keyed by `UserId` so those sites become O(1) lookups. The whole trick is keeping
the index in sync with `clients` — it's only mutated in two places (connect /
disconnect), so that part is small.

**Scan sites (verified against current main.rs):**
- `evict_existing_user` — `main.rs:2367` (`clients.iter().filter(|(_, c)| c.user_id == user_id)`)
- `internal_push_user` — `main.rs:2614`
- `internal_disconnect_user` — `main.rs:2710`
- `handle_request_peer_presence` partner lookup — `main.rs:1157` (`clients.values().find(|c| c.user_id == partner_id)`)
- **Fifth site (not in the original list):** the spawned hydrate-task snapshot in
  `handle_socket` at `main.rs:413` — same `.values().find(|c| c.user_id == partner_id)`
  partner-lookup pattern, with a trailing `.filter(sesh_presence_allowed)` + `.map(...)` to keep.

**Do NOT touch** (look similar, index doesn't apply):
- `main.rs:1286` — `for c in clients.values_mut()` with predicate `user_id == user_id || Some(c.user_id) == partner_id`. Two-key OR-predicate *write* over both peers, not a single-user lookup.
- `main.rs:2532` / `2552` — `exclude_user_id` checks while already iterating a *room's* member set, not a full-clients scan. Already O(room size).

---

### Part A — Add and initialize the index

**Step 1. Add the field to `AppState`** (`main.rs:107`, under `clients`):

```rust
clients: Arc<RwLock<HashMap<ClientId, Client>>>,
user_clients: Arc<RwLock<HashMap<UserId, HashSet<ClientId>>>>,
```

`HashSet` not `Vec` — a user can briefly have two client_ids during an eviction overlap.

**Step 2. Initialize in `main`** (`main.rs:244`, under the `clients:` line):

```rust
clients: Arc::new(RwLock::new(HashMap::new())),
user_clients: Arc::new(RwLock::new(HashMap::new())),
```

Checkpoint: `cargo build` should be clean (unused-field warning at most).

---

### Part B — Keep the index in sync (the two write sites)

**Lock rule:** when holding both, always lock `clients` *before* `user_clients`.
The read sites in Part C never hold both at once, so this rule alone prevents deadlock.

**Step 3. On connect** — `handle_socket`, inside the existing `clients.write()` block
at `main.rs:350-385`, after `clients.insert(...)` and before the block closes:

```rust
let mut user_clients = state.user_clients.write().await;
user_clients
    .entry(user_id)
    .or_default()
    .insert(client_id.clone());
```

**Step 4. On disconnect** — `disconnect_cleanup`. The `client` is fetched at
`main.rs:2324` but it's *moved into* the `if let Some(client)` arm, while the
removal block lives *after* that arm — so capture the id up front from the
`Option`, before the `if let`, so it's still in scope at removal:

```rust
let client = get_client(state, client_id).await;
let user_id = client.as_ref().map(|c| c.user_id);
```

Then in the removal block (after `clients.remove(client_id)`), guard on the
`Option`:

```rust
if let Some(user_id) = user_id {
    let mut user_clients = state.user_clients.write().await;
    if let Some(set) = user_clients.get_mut(&user_id) {
        set.remove(client_id);
        if set.is_empty() {
            user_clients.remove(&user_id);
        }
    }
}
```

The empty-set cleanup matters — otherwise the index leaks dead user entries over uptime.

Note: `evict_existing_user` does NOT call `disconnect_cleanup` — it only sends a
close frame. The dying old socket's own `disconnect_cleanup` removes it later. The
set keying lets the new and old client_ids coexist correctly in the meantime, so
no extra removal is needed there.

Checkpoint: build again. Index is maintained but not yet read — behavior unchanged.

---

### Part C — Convert the scan sites to lookups

**Pattern for all five:** snapshot the id set under `user_clients.read()`, drop that
guard, then read `clients`. Never hold both at once.

**Step 5. `internal_push_user`** (`main.rs:2614`):

```rust
let txs: Vec<Tx> = {
    let ids = {
        let user_clients = state.user_clients.read().await;
        user_clients.get(&body.user_id).cloned()
    };
    match ids {
        Some(ids) => {
            let clients = state.clients.read().await;
            ids.iter().filter_map(|id| clients.get(id).map(|c| c.tx.clone())).collect()
        }
        None => Vec::new(),
    }
};
```

**Step 6. `internal_disconnect_user`** (`main.rs:2710`): identical shape, same `body.user_id`.

**Step 7. `evict_existing_user`** (`main.rs:2367`): keep both id and tx:

```rust
let to_evict: Vec<(ClientId, Tx)> = {
    let ids = {
        let user_clients = state.user_clients.read().await;
        user_clients.get(&user_id).cloned()
    };
    match ids {
        Some(ids) => {
            let clients = state.clients.read().await;
            ids.iter()
               .filter_map(|id| clients.get(id).map(|c| (id.clone(), c.tx.clone())))
               .collect()
        }
        None => Vec::new(),
    }
};
```

**Step 8. `handle_request_peer_presence` partner lookup** (`main.rs:1157`):

Note: use `match`, not `ids.and_then(|ids| { ... .await })` — `.await` isn't
allowed inside a non-async closure.

```rust
let partner = {
    let ids = {
        let user_clients = state.user_clients.read().await;
        user_clients.get(&partner_id).cloned()
    };
    match ids {
        Some(ids) => {
            let clients = state.clients.read().await;
            ids.iter().find_map(|id| clients.get(id).cloned())
        }
        None => None,
    }
};
```

**Step 9. Hydrate-task snapshot** (`main.rs:413`) — keep the trailing `.filter` and
`.map`, and note this uses `bg_state` (the cloned state inside the spawned task):

```rust
let partner_snapshot = {
    let ids = {
        let user_clients = bg_state.user_clients.read().await;
        user_clients.get(&partner_id).cloned()
    };
    match ids {
        Some(ids) => {
            let clients = bg_state.clients.read().await;
            ids.iter()
               .find_map(|id| clients.get(id))
               .filter(|c| sesh_presence_allowed(c))
               .map(|c| (c.user_id, c.friend_light_color.clone(), c.friend_dark_color.clone(), c.gecko_game_level))
        }
        None => None,
    }
};
```

---

### Step 10. Validate

1. `cargo build --release` clean.
2. Run `loadtest/` against the baseline scenario; compare CPU + p50/p99 broadcast latency.
3. Gain scales with concurrent users — flat at low N is expected; the point is killing
   the O(N) connect/evict cost at scale. If it doesn't move the numbers and adds
   noticeable complexity, revert and move on.

Test note: connect/disconnect churn is where index correctness shows. Hammer reconnects
in the loadtest and confirm presence still resolves correctly — that exercises the
Part B insert/remove sync harder than steady-state coord traffic does.

---

## Validation plan

After each item:
1. `cargo build --release` clean.
2. Run the loadtester (`loadtest/`) with the same scenario as the baseline; record CPU on the droplet (or local) and p50/p99 broadcast latency.
3. If a change doesn't show up in the numbers, revert and move on rather than carrying dead complexity.
