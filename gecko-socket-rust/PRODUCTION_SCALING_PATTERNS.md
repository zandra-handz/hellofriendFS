# Production scaling patterns

How real production codebases handle the "websocket service needs data from the app database" problem, and where this project sits today. Reference doc — not a TODO list.

---

## The core problem

Every websocket connect currently triggers Django HTTP calls (`live-sesh-context`, `check-host-link-and-load`) that grab Postgres connections. On a managed Postgres tier with ~22 slots, a connect storm exhausts the pool and connects start failing with `OperationalError: remaining connection slots are reserved`. This is the architectural wall behind the N=100-vs-N=200 ceiling we hit during loadtesting.

Production systems solve this in layers — they don't pick one. Stack them as load demands.

---

## The patterns

### 1. Bake data into the auth token (JWT claims)

Cheapest, most common starting move. Used by Discord, Slack, Linear, Figma in some form.

When the user logs in, auth mints a JWT containing not just `user_id` but the small metadata the realtime service needs (`partner_id`, `is_host`, `friend_id`, etc.). The websocket server validates the JWT cryptographically and reads the claims directly. **Zero DB calls on connect.**

Tradeoff: JWT goes stale if state changes. Mitigated by short TTLs (5–15 min) plus refresh tokens. FE refetches the token when sesh state changes.

For this project: removes `live-sesh-context` entirely.

### 2. Connection pooler in front of Postgres (pgbouncer / RDS Proxy / Cloud SQL Proxy)

The single answer to "Postgres slot exhaustion." Almost every production Django/Rails/Node deployment has one.

pgbouncer sits between the app and Postgres. The app opens 200 connections to pgbouncer; pgbouncer multiplexes those onto ~20 actual Postgres connections by reusing them across requests. Postgres only ever sees pgbouncer's small pool.

DigitalOcean managed Postgres has built-in pgbouncer — flip a toggle in the panel, get a separate connection-pool URL, point Django at it. AWS RDS Proxy and GCP Cloud SQL Auth Proxy are equivalents.

For this project: this alone probably bumps the loadtest ceiling from N=100 to N=300+ without changing any code.

### 3. Cache layer (Redis / Memcached) for hot lookups

When data changes infrequently relative to read frequency, cache it. The realtime service reads from Redis (sub-ms, scales to millions of reads/sec) instead of Django. Cache invalidation happens via Django publishing an event (Redis pub/sub, Kafka, NATS) when state changes — the websocket service listens and updates its local cache.

Used by Twitch, Slack realtime, most chat platforms for presence, mute state, room membership, etc. The websocket server holds an in-memory copy that gets pushed updates. No connect-time DB call.

For this project: a Rust-side LRU cache with 30s TTL on the hydrate response would absorb 90%+ of Django calls during a reconnect storm.

### 4. Read replicas + write/read split

Production Postgres has a primary for writes and multiple replicas for reads. The realtime service hits replicas for its lookups. Each replica has its own slot pool — total DB capacity scales linearly with replicas. Combined with pgbouncer, comfortably supports tens of thousands of concurrent connections.

For this project: not needed at current scale. Useful when single-instance Postgres becomes the bottleneck.

### 5. Horizontal scaling + sticky routing

Multiple websocket server instances behind a load balancer. Each handles its share. Sticky routing (consistent hashing on user_id) ensures pair-based features land both sides on the same node — broadcasts stay in-process, no cross-node fanout.

When cross-node fanout *is* needed (presence updates everyone subscribes to), it goes through Redis pub/sub or NATS. Slack's "flannel" gateway architecture is the canonical write-up.

For this project: future work when one droplet runs out of CPU.

### 6. Stateful session gateways (the "Discord pattern")

The realtime service is the source of truth for ephemeral state — "who's connected, who's in what room, what they're doing right now" — and this never goes back to the DB during steady state. The DB stores persistent state (users, friends, history); the realtime service stores ephemeral state (online presence, current room, current activity).

On connect, the realtime service writes ephemeral state into memory and only consults the DB for *persistent* facts (which it then caches). Combined with pattern 3, the DB sees one read per user per refresh-cycle, not one per connect.

For this project: this is the long-term shape. The Rust process already holds ephemeral state correctly; what's missing is local caching of the persistent facts so they aren't re-fetched on every reconnect.

---

## Practical mapping for this project

Ordered by leverage / effort:

| Step | Effort | Impact |
|---|---|---|
| **A.** Turn on DigitalOcean's built-in pgbouncer (panel toggle, point Django at the pool URL) | ~5 minutes | Bumps loadtest ceiling from N=100 → N=300+, zero code change |
| **B.** Bake `partner_id` / `is_host` / `friend_id` into the gecko-socket JWT | ~1 day | Removes `live-sesh-context` call entirely; near-zero DB load on connect |
| **C.** Add Rust-side hydrate cache (`HashMap<UserId, (Snapshot, Instant)>`, 30s TTL) | ~1 hour | 90%+ reduction in Django calls during reconnect storms |
| **D.** Add Redis pub/sub for sesh state change invalidation | 2–3 days | Production-grade cache invalidation; lets C use a longer TTL safely |
| **E.** Horizontally scale Rust (>1 node behind a load balancer with sticky routing) | Days | Real growth headroom for 10x+ users |

**A and C are the immediate practical wins.** A is free and instant. C is small, lands in one PR.

**B is the "do it once, never worry again" move** but requires coordinated changes in Django (JWT minting), Rust (read claims), and FE (refetch token when sesh changes). Worth doing before user count grows past a few thousand active sessions.

**D and E are scale-stage problems** — they matter once you've outgrown a single droplet. Don't spend time on them yet.

---

## What NOT to do at this stage

- **Don't bump the Postgres tier as a first move.** Pattern 2 (pgbouncer) gets you most of the same headroom for free. Bumping the tier without pgbouncer just delays the slot-exhaustion wall.
- **Don't add Redis just for caching.** Pattern 3 in Rust memory is simpler at this size; Redis only earns its keep when you have multi-node fanout (pattern 5) or cross-service invalidation.
- **Don't connect Rust directly to Postgres** (sqlx, tokio-postgres) yet. Cleanly bypasses Django but couples Rust to the schema. Worth it only if Django proxying becomes the bottleneck, which won't happen at this scale once A+C are in place.
- **Don't optimize the websocket fanout path further** — items 1–4 in `RESCUING_RUST_HOTPATH.md` already moved this past the realistic bottleneck. The connect path (Django, Postgres) is now where every minute of optimization buys the most.

---

## Reference: what big platforms actually do

A grab-bag of public writeups for further reading. Not required, just useful to know they're solving the same problems:

- **Discord:** Erlang/Elixir gateways with sticky-by-user routing, Redis for ephemeral state, MongoDB+Cassandra for persistent. Public blog "How Discord Stores Trillions of Messages" and "How Discord Handles 5 Million Concurrent Voice Users."
- **Slack:** "flannel" gateway architecture — sticky-routed nodes, Redis pub/sub for cross-node events, MySQL primary + read replicas, memcached cache layer.
- **Figma:** Multiplayer state lives in a custom CRDT engine in Rust, persistent state in Postgres. JWT carries minimal claims; everything else is in-memory.
- **Linear:** Sync engine pattern — clients hold a local cache, server pushes deltas. JWT for auth; bulk reads from a read-optimized cache layer.

The shared pattern across all of them: **persistent state in the DB, ephemeral state in the realtime service, hot reads cached, invalidation via events.** Nothing exotic — just disciplined layering.
