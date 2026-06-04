# Gecko Socket — Scalability & Performance Refactor Plan

Goal: make `gecko-socket-rust/src/main.rs` as scalable and performant as a
single-node server can be, without a risky big-bang rewrite.

This document covers **Tier 1 (single-node, done right)**. Tier 2 (multi-node
Redis pub/sub backplane) and Tier 3 (replace with Centrifugo) are out of scope
for now — see the "Deferred tiers" note at the bottom.

---

## Why we're doing this

The current shared state is:

```rust
clients: Arc<RwLock<HashMap<ClientId, Client>>>
rooms:   Arc<RwLock<HashMap<RoomName, Arc<HashSet<ClientId>>>>>
```

Three defects show up at scale (and waste cycles even at small scale):

1. **One global lock over all connections.** Every broadcast takes it for
   reads; every `set_friend` / `set_guest_on_screen` / hydrate takes it for
   writes. Writers stall all readers process-wide.

2. **O(n) scans by `user_id`.** Several paths walk every connected client to
   find one by `user_id` (presence, eviction, internal push/disconnect). On a
   reconnect storm this is O(n^2).

3. **Fat clone on every handler entry.** `get_client` clones the entire
   `Client` struct (~11 heap-allocating `String`/`Option<String>` fields) just
   to read a few fields.

The plan fixes all three in phases. **Each phase compiles and ships on its
own** — do not merge them into one change.

---

## THE ONE PITFALL TO INTERNALIZE FIRST

The current code deliberately holds a lock guard **across `.await`**, e.g. in
`handle_update_gecko_position`:

```rust
let clients = state.clients.read().await;          // tokio RwLock guard
let Some(c) = clients.get(client_id) else { return };
// ...
broadcast_position_to_room(state, &clients, ...).await;   // guard held across .await
```

That is **safe** with `tokio::sync::RwLock` (async-aware).

It is **NOT safe** with `DashMap`. `DashMap` is a synchronous (parking_lot)
lock. Holding a `DashMap` `Ref`/`RefMut` across an `.await` parks the OS thread
and can deadlock the executor.

**Rule for the whole migration:** grab what you need → drop the ref → THEN
await. Every spot that currently holds the guard across an await must be
rewritten this way. This is the entire reason the work is staged.

---

## PHASE 1 — Shard the maps (removes the global lock + O(n) scans)

`Client` stays fat for now. We only change the container and the access
pattern.

### 1a. Add the dependency

`gecko-socket-rust/Cargo.toml`:

```toml
dashmap = "6"
```

(Open question: add `dashmap`, or hand-shard with `Vec<Mutex<HashMap>>` to
avoid the crate. Default recommendation: use `dashmap` — it's the standard.)

### 1b. Change `AppState` (around main.rs:106)

```rust
clients:    Arc<DashMap<ClientId, Client>>,
rooms:      Arc<DashMap<RoomName, HashSet<ClientId>>>,   // plain HashSet; DashMap shards for you
user_index: Arc<DashMap<UserId, HashSet<ClientId>>>,     // reverse index: user_id -> client_id(s)
```

Note: `rooms` value drops the inner `Arc<HashSet>`. That Arc existed only to
cheaply clone the set out from under the global lock. With DashMap you collect
the ids under a short-lived shard lock instead.

### 1c. Make `get_client` sync (no global lock, no await)

```rust
fn get_client(state: &AppState, client_id: &str) -> Option<Client> {
    state.clients.get(client_id).map(|r| r.clone())   // ref dropped at end of expression
}
```

It is no longer `async`. Drop `.await` at all call sites — the compiler will
list every one.

### 1d. Rewrite every "hold guard across await" site (extract → drop → await)

Position handlers are the important ones. Pattern for
`handle_update_gecko_position`:

```rust
async fn handle_update_gecko_position(state: &AppState, client_id: &str, data: Option<Value>) {
    let mut payload = data.unwrap_or_else(|| json!({}));

    // short critical section: copy out the few fields, drop the ref
    let (user_id, friend_id, shared_room) = {
        let c = match state.clients.get(client_id) {
            Some(c) if c.friend_id.is_some() && sesh_presence_allowed(&c) => c,
            _ => return,
        };
        (c.user_id, c.friend_id, c.shared_room.clone())
    }; // <-- ref dropped HERE, before any await

    if let Value::Object(map) = &mut payload {
        map.entry("position".to_string()).or_insert_with(|| json!([0, 0]));
        map.entry("energy".to_string()).or_insert_with(|| json!(1.0));
        map.insert("from_user".to_string(), json!(user_id));
        map.insert("friend_id".to_string(), json!(friend_id));
    }

    let Some(encoded) = encode_outgoing(&OutgoingMessage {
        action: "gecko_coords".to_string(),
        data: payload,
    }) else { return };

    broadcast_position_to_room(state, &shared_room, user_id, "gecko_coords", encoded).await;
}
```

Apply the same shape to:
- `handle_update_host_gecko_position`
- `handle_update_guest_gecko_position`
- `handle_update_capsule_progress`
- `handle_send_all_host_capsules`

### 1e. Broadcast helpers look recipients up themselves

The helpers no longer receive a `&HashMap` guard. They collect the room's
client_ids under a short lock, drop it, then iterate. `try_send` is sync, so
there is no await inside the loop.

```rust
async fn broadcast_position_to_room(
    state: &AppState,
    room_name: &str,
    exclude_user_id: UserId,
    action: &str,
    encoded: Message,
) {
    let recipients: Vec<ClientId> = match state.rooms.get(room_name) {
        Some(set) => set.iter().cloned().collect(),   // copy ids, drop room ref
        None => return,
    };
    for cid in recipients {
        if let Some(c) = state.clients.get(&cid) {
            if c.user_id == exclude_user_id { continue; }
            c.position_slots.put(action, encoded.clone());
        }
    }
}
```

Apply the same "collect ids → drop → iterate" pattern to:
- `broadcast_to_room`
- `broadcast_to_room_with_clients` (drops the `&clients` param)
- `broadcast_peer_presence_online_to_room`
- `internal_push_room`

### 1f. `join_room` / `leave_room` become trivial

```rust
fn join_room(state: &AppState, room_name: &str, client_id: &str) {
    state.rooms.entry(room_name.to_string()).or_default().insert(client_id.to_string());
}

fn leave_room(state: &AppState, room_name: &str, client_id: &str) {
    if let Some(mut set) = state.rooms.get_mut(room_name) {
        set.remove(client_id);
    }
    state.rooms.remove_if(room_name, |_, set| set.is_empty());
}
```

(These can stop being `async` too.)

### 1g. Maintain `user_index` in the THREE membership-changing spots

Only three places change `clients` membership — keep the index in lockstep
there, in the same critical section:

- **Insert** (`handle_socket`, ~main.rs:351): after inserting into `clients`,
  `user_index.entry(user_id).or_default().insert(client_id.clone());`
- **Remove** (`disconnect_cleanup`, ~main.rs:2189): after `clients.remove`,
  remove `client_id` from `user_index[user_id]`; drop the `user_id` key if its
  set is now empty (else you leak empty sets).
- **Evict** (`evict_existing_user`): ensure the evicted client's removal also
  prunes the index (or that it ends via the normal disconnect path).

Use a `HashSet<ClientId>` value (not a bare `ClientId`): during the
evict-then-insert overlap a user can momentarily have two client_ids. Steady
state is one element, so the cost is negligible.

### 1h. Replace the five O(n) scans with index lookups

Rewrite these to go through `user_index` (O(1)) instead of
`clients.values().find(...)`:

- `evict_existing_user` (main.rs:2203)
- `internal_push_user` (main.rs:2449)
- `internal_disconnect_user` (main.rs:2545)
- `handle_request_peer_presence` (main.rs:1148)
- the connect-spawn `partner_snapshot` (main.rs:413)

Lookup shape:

```rust
let client_ids: Vec<ClientId> = match state.user_index.get(&partner_id) {
    Some(set) => set.iter().cloned().collect(),
    None => return /* offline */,
};
// then state.clients.get(&cid) for each
```

### Phase 1 done = global lock gone + O(n) scans gone

`Client` is still fat and `get_client` still clones it, but there is no global
contention anymore. **Ship it. Watch for a day before Phase 2.**

---

## PHASE 2 — Thin the clone (kills the fat `get_client` allocation)

Audit which `Client` fields are read **cross-client** (for a client that is not
the handler's own). In this codebase that is a short list:

- presence-gate fields: `is_host`, `friend_id`, `sesh_friend_id`, `guest_on_screen`
- `user_id`
- `friend_light_color`, `friend_dark_color`

Everything else (`partner_*`, `gecko_*`, `partner_points`, rooms, etc.) is read
only for the current client.

### Lower-risk option (recommended): `Arc<str>` the string fields

Change the `String` / `Option<String>` fields on `Client` to
`Arc<str>` / `Option<Arc<str>>`:

```rust
own_room: Arc<str>,
shared_room: Arc<str>,
partner_room: Option<Arc<str>>,
partner_username: Option<Arc<str>>,
partner_friend_name: Option<Arc<str>>,
friend_light_color: Option<Arc<str>>,
friend_dark_color: Option<Arc<str>>,
gecko_message: Option<Arc<str>>,
gecko_emotion: Option<Arc<str>>,
gecko_message_kind: Option<Arc<str>>,
gecko_message_ref_id: Option<Arc<str>>,
```

Then `get_client`'s clone is a handful of refcount bumps instead of ~11 heap
allocations. Mechanical change (the compiler finds every assignment site — use
`.into()` / `Arc::from(s)`), no control-flow restructuring.

This captures ~80% of the clone win for ~20% of the risk of the full actor
split.

### Phase 2 done = no global lock, no O(n) scans, no fat clone

This is the recommended stopping point. The entire performance defect is gone.
**Only proceed to Phase 3 with profiler evidence that contention remains.**

---

## PHASE 3 — Actor model (OPTIONAL, only if measurements demand it)

End-state: the shared registry holds a thin handle; private session state is
owned by the connection task with zero shared locking.

```rust
struct Handle {              // in the sharded registry
    user_id: UserId,
    tx: mpsc::Sender<Message>,
    position_slots: Arc<PositionSlots>,
    // presence-gate fields must stay shared (peers read them):
    is_host: bool,
    friend_id: Option<u64>,
    sesh_friend_id: Option<u64>,
    guest_on_screen: bool,
    friend_light_color: Option<Arc<str>>,
    friend_dark_color: Option<Arc<str>>,
}
```

All genuinely-private state (gecko message, points, partner metadata, rooms)
moves into a struct **owned by `recv_task`**, mutated with no shared lock.

### Why it's a HYBRID, not a pure actor model

`sesh_presence_allowed` reads a **peer's** gate fields. Those cannot be hidden
inside the peer's task, so they stay in the shared `Handle` and are updated on
`set_friend` / `set_guest_on_screen` / hydrate / leave. Only the truly-private
fields go local.

This is the most performant form and also where presence can break subtly.
That is why it is explicitly last.

---

## Recommended execution order

1. **Phase 1** — shard + user_index. Single reviewable diff on a branch. The
   across-await rewrites (1d/1e) are where a mistake would hide, so review
   those carefully.
2. **Phase 2** — `Arc<str>` the strings. Mechanical, compiler-guided.
3. **Stop.** Only do **Phase 3** if profiling proves contention remains.

Do NOT build the Redis pub/sub backplane (multi-node) until one droplet is
provably not enough — it adds a network hop per broadcast plus a failure model,
and is premature for a single-droplet product.

---

## Deferred tiers (not in scope now, recorded for later)

- **Tier 2 — Horizontal scale.** Redis pub/sub backplane (Redis already in the
  stack): each node subscribes to room channels; a broadcast publishes to
  Redis and every node delivers to its local sockets. Presence in Redis with
  heartbeat TTL. nginx sticky sessions for the WS upgrade. Add only when one
  box isn't enough.
- **Tier 3 — Buy instead of build.** Centrifugo does presence + rooms + Redis
  backplane out of the box, but heavy domain logic (gecko state, points
  binding, friend gating, Django proxying) is welded into this socket, so a
  rewrite likely costs more than it saves. Flagged for completeness only.

---

## Constraints to respect (project rules)

- Rust WS must NOT touch the DB directly — all DB work goes through Django.
  Keep cross-node / persistence concerns flowing through Redis + Django the way
  hydrate/seed already do.
- New socket pushes get NEW event types — never overload existing event_type
  strings.
