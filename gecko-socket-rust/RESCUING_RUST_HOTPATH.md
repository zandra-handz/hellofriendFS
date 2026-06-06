# RESCUING RUST HOTPATH

Cleanup pass on `gecko-socket-rust/src/main.rs` to free CPU on the 1 vCPU droplet. Hot path = the gecko-coord broadcasts that fire many times per second per session: `update_gecko_position`, `update_host_gecko_position`, `update_guest_gecko_position`, `update_capsule_progress`, plus `broadcast_to_room` itself.

## Status (audited 2026-06-06 against main.rs)

**Items 0–5 are all implemented.** What's documented below as "Do" was the original
plan; the **What shipped** note on each item records what's actually in the code,
which sometimes differs from (and improves on) the proposal.

The only work left is the **item 3 stretch goal** (forward raw msgpack bytes, skip the
`Value` round-trip) — and that's gated on profiling, not yet justified. See
[Remaining work](#remaining-work) at the bottom.

There's also an optimization in the code that predates / isn't in this list — the
`PositionSlots` latest-wins coalescer; see [Bonus](#bonus-positionslots-coalescer).

> ⚠️ Line numbers throughout drift as the file changes — they're hints, grep the
> symbol names. The audit confirmed the *symbols* exist; the numbers may be stale.

---

## 0. Switch `println!` -> `tracing` with non-blocking writer
**Status:** done.

`tracing` + `tracing_appender::non_blocking` is wired in `main`. All call sites use `info!` / `warn!` / `error!` / `debug!`. The peer-presence and hydrate logs are now `debug!` so they're off by default in prod (set `RUST_LOG=info` or higher).

---

## 1. Stop cloning the whole `Client` on every coord update
**Status:** ✅ done.

`get_client()` returns a fully-cloned `Client` — when the hot-path callers only need `(user_id, friend_id, is_host, shared_room)`.

**What shipped:** all five hot-path handlers (`handle_update_gecko_position`,
`handle_update_host_gecko_position`, `handle_update_guest_gecko_position`,
`handle_update_capsule_progress`, `handle_send_all_host_capsules`) take a
`state.clients.read()` guard, `clients.get(client_id)`, and read just the fields
they need off the borrow — no full-`Client` clone. The proposed `CoordCtx` helper
was not built; instead they keep the read guard live and hand `&clients` straight
to the broadcast helper (see item 2), which is strictly better. `get_client` is
still used on the cold paths (`handle_join_live_sesh`, `handle_request_peer_presence`,
`disconnect_cleanup`, etc.).

---

## 2. Collapse the two RwLock acquires per broadcast
**Status:** ✅ done via option (a).

Old path was 3 lock ops/frame: `clients.read()` (dropped), then `rooms.read()`, then `clients.read()` again.

**What shipped:** option (a). The hot-path handlers hold one `clients.read()` guard
and pass `&clients` into `broadcast_position_to_room` / `broadcast_to_room_with_clients`
(main.rs ~2559 / ~2581), which only add a single `rooms.read()`. Net: 2 lock ops/frame,
no redundant second `clients.read()`. Option (b) (DashMap) was **not** done — correctly,
since the doc gated it on profiling still showing contention. Revisit (b) only if a
profile at hundreds of concurrent sessions shows the global `RwLock` as the bottleneck.

---

## 3. Stop parse->rebuild->re-serialize on every coord frame
**Status:** ✅ done (in-place mutation). Stretch goal still open — see [Remaining work](#remaining-work).

Old pattern rebuilt a brand-new `json!{...}` from ~9 `.cloned()` fields every frame, then re-serialized that fresh map.

**What shipped:** every coord handler now mutates the incoming `Value` in place and
forwards it as-is — no clone-and-rebuild. e.g. `handle_update_host_gecko_position`:

```rust
let mut payload = data.unwrap_or_else(|| json!({}));
// ...read user_id/friend_id/shared_room off the clients read guard...
if let Value::Object(map) = &mut payload {
    map.entry("steps".to_string()).or_insert_with(|| json!([]));
    // ...defaults for the other fields via .entry().or_insert_with()...
    map.insert("from_user".to_string(), json!(user_id));
    map.insert("friend_id".to_string(), json!(friend_id));
}
let encoded = encode_outgoing(&OutgoingMessage { action: "host_gecko_coords".into(), data: payload })?;
broadcast_position_to_room(state, &clients, &shared_room, user_id, "host_gecko_coords", encoded).await;
```

Saved the ~9 clones + fresh map alloc per frame. **Still per-frame:** the
`rmp_serde::from_slice` decode on the way in and the `encode_outgoing`
(`to_vec_named`) re-encode on the way out — that's what the stretch goal targets.

---

## 4. Don't await Django HTTP calls inline on the recv task
**Status:** ✅ done.

Blocking the websocket recv task on a Django round-trip (potentially seconds, since gunicorn/uvicorn workers contend for the same 1 vCPU) stalls that connection.

**What shipped:**
- The `handle_socket` connect-time hydrate runs inside a `tokio::spawn` (main.rs ~405,
  uses a `bg_state`/`bg_client_id` clone) — recv loop is not blocked on it.
- `handle_join_live_sesh` (main.rs ~959) is fully wrapped in a single `tokio::spawn`.
  Ordering is preserved inside that one spawn — `join_live_sesh_ok` is sent before
  `proxy_check_host_link_and_load` runs — exactly the caveat's requirement, and it
  was *not* split into parallel spawns.

---

## 5. Index clients by `user_id` to kill linear scans
**Status:** ✅ done in code (`cargo check` clean). Loadtest validation (step 10.2/10.3) still pending. Full implementation record kept below.

> Note for scale context: at ~200 concurrent users the O(N)→O(1) change is
> microseconds — not a measurable CPU win. Its value is removing the O(N²)
> connect-storm cliff and shortening lock-hold times. Bank it as headroom; don't
> expect the loadtest p50 to move at this N.

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

## Bonus: `PositionSlots` coalescer

Not on the original list, but in the code and worth recording. `broadcast_position_to_room`
(main.rs ~2559) does **not** push coord frames onto the ordered mpsc. Instead it routes
each recipient through `client.position_slots.put(action, encoded)` — a latest-wins slot
per action. If a recipient's consumer falls behind, a newer coord frame *overwrites* the
stale pending one rather than queueing behind it.

Why it matters at scale: bounded per-client memory and no head-of-line buildup when a
slow client can't keep up with ~2,000 frames/s aggregate. For real-time position this is
correct (you only ever care about the latest position), and it's arguably a bigger
throughput safeguard at 200 users than anything else on this list. Non-position relays
(`all_host_capsules`, `capsule_progress`) still go through `broadcast_to_room_with_clients`
→ the ordered `try_send`, which is right — those aren't latest-wins.

---

## Remaining work

Everything on the numbered list (0–5) is implemented. One open item:

**Item 3 stretch goal — forward raw msgpack bytes.** Each coord frame still pays an
`rmp_serde::from_slice` (decode to `Value`) on ingress and an `encode_outgoing`
(`to_vec_named`) on egress. At ~2,000 frames/s on 1 vCPU that's the remaining hot-path
CPU. The fix is to forward the inbound bytes with a minimal header tweak instead of the
`Value` round-trip.

**Do not start this blind — it's gated on profiling.** First:
1. `cargo build --release`, run `loadtest/` at ~200 users (and a 2× headroom run).
2. Profile and confirm `rmp_serde::from_slice` / `to_vec_named` actually dominate the
   coord path. If they don't, this is dead complexity — stop here, the list is done.
3. If they do dominate, the relay handlers need the from_user/friend_id injection to
   happen without a full `Value` parse (e.g. patch the encoded map, or carry the
   injected fields in an envelope), which is the invasive part — design it then.

## Validation plan (per change)

1. `cargo build --release` clean. (Note: the dev box has hit paging-file OOM during
   full release codegen — `cargo check` for type-level validation, close other apps or
   raise the Windows page file for the release build.)
2. Run `loadtest/` with the baseline scenario; record CPU on the droplet (or local) and
   p50/p99 broadcast latency.
3. If a change doesn't show up in the numbers, revert rather than carry dead complexity.
