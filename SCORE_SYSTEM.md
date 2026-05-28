# Gecko Score System

How points get into the database. There are now **two distinct award paths** —
`gecko activity` (FE-initiated, streak-aware, sesh-aware) and `event award`
(BE-initiated, no streak, no sesh). Both end at `GeckoPointsLedger` and both
bump per-user / per-friend lifetime totals, but the surrounding behavior is
different. Keep them straight.

## Paths overview

| Path | Trigger | Multiplier | Live-sesh scoreboard | Socket event |
|---|---|---|---|---|
| **gecko activity** (steps, scripted points) | FE WS `update_gecko_data` / `request_points` | active streak applies | accrued when peer present | `points_update` / `points_awarded` |
| **event award** (hello created, future game wins etc.) | BE view inside a `transaction.atomic()` | always 1 | never | `hello_points` (one event per source) |

## End-to-end flow — gecko activity path

```
RN client
  │  WebSocket: { action: "update_gecko_data", data: { points_earned, score_state, steps, distance, ... } }
  ▼
Rust socket  (gecko-socket-rust/src/main.rs)
  │  HTTPS POST (msgpack), header X-Rust-Internal-Secret
  │  Concurrency cap: 10 in-flight Django calls per Rust process
  ▼
Django REST endpoint  POST /users/internal/gecko/socket-action/
  │  Auth: X-Rust-Internal-Secret matches settings.RUST_INTERNAL_SECRET
  │  Dispatched in _gecko_socket_action_dispatch (users/views.py:1495)
  ▼
gecko_score_helpers.apply_gecko_data_update(user, friend_id, payload)
  ▼
DB writes:
  - GeckoScoreState  (streak fields)
  - GeckoData / GeckoCombinedData / GeckoPointsLedger  (via process_gecko_data)
  ▼
Returns { "status": "ok" } back through Rust to FE
```

The Rust socket holds zero score state — it is a pure relay for score-related actions. All DB work is on Django.

## Authority model

| Concern                        | Authoritative side |
| ------------------------------ | ------------------ |
| What scoring events fired      | FE                 |
| How much each event is worth   | BE                 |
| Multiplier caps                | BE                 |
| Streak duration caps           | BE                 |
| Whether a streak can start     | BE                 |
| Steps / distance counters      | FE (raw deltas)    |

The BE never independently detects activity or schedules point awards in the gecko system. If the FE never sends a `points_earned` entry, no gecko points are ever awarded for that event — full stop. But the BE owns the *amount* and refuses to honor anything the FE invents (rule lookup + label cross-check, see below).

## Point values

Stored in `geckoscripts.models.ScoreRule` as rows of `(code, label, points, version)`. The active set is `version=1`.

Loaded by `_load_score_rules()` (gecko_score_helpers.py:188) and cached at module level for 5 minutes (`_SCORE_RULES_TTL_SECONDS = 300`). Cache is per-process — each gunicorn worker pays one `SELECT * FROM scorerule WHERE version=1` per 5-minute window. After bumping rules, workers serve stale values for up to 5 minutes.

## Resolution: `_build_pending_entry` (gecko_score_helpers.py:382)

For each `update_gecko_data` payload, the FE sends:

```json
{
  "points_earned": [
    { "code": <int>, "label": <str>, "timestamp_earned": <iso8601> },
    ...
  ]
}
```

For each entry the BE:

1. Looks up `rule = score_rules.get(code)`.
2. **Drops the entry silently** if the rule doesn't exist OR if `rule.label != label` (line 420). This is the security gate — FE cannot invent codes or relabel rules.
3. Picks the multiplier (lines 428–432):
   - If a streak is active (`streak_expires_at` exists AND `ts < streak_expires_at`) → `active_multiplier`
   - Otherwise → `base_multiplier`
4. Computes amount: `rule.points * applied_multiplier`.

`total_points` for the entry is the sum of resolved amounts.

## Streaks

FE initiates, BE gates and caps.

### Trigger

FE includes a `score_state` block in the `update_gecko_data` payload:

```json
{
  "score_state": {
    "multiplier": <int>,
    "expiration_length": <seconds>
  }
}
```

### BE handling (gecko_score_helpers.py:456–483)

1. **Already-active streak blocks new ones** (line 458): if `ss["expires_at"]` exists and is still in the future, the entire `score_state` block is ignored. No restarting, no extending an in-flight streak.
2. **Multiplier capped** at `max_score_multiplier` (sourced from `GeckoScoreState`). Requests above the cap are silently clamped down.
3. **Expiration capped** at `max_streak_length_seconds`. Requests above the cap fall back to the cap.
4. After clamping: `ss["multiplier"] = clamped_value`, `ss["expires_at"] = now + length_seconds`.

## What gets persisted

In `apply_gecko_data_update` (gecko_score_helpers.py:488), two writes:

### 1. Streak state (lines 515–522)

`GeckoScoreState.objects.update(multiplier=..., expires_at=..., last_steak_expiry=...)`

Only the streak fields. Energy is FE-derived and not persisted on every update.

### 2. Cumulative totals + ledger (lines 524–535)

Calls `gecko_helpers.process_gecko_data(...)` with `points_pre_resolved=True`, which:

- Increments `GeckoData.total_steps`, `total_distance`, `total_duration`, `total_points` via `F()` expressions (atomic). *Per-friend totals.*
- Increments `UserLifetimeTotals.total_steps`, `total_distance`, `total_duration`, `total_gecko_points` via `F()` expressions. *Per-user grand totals.* Only fields with non-zero deltas are included — pure point awards skip the UPDATE entirely.
- Bulk-creates `GeckoPointsLedger` rows for each resolved point entry.
- Updates hourly bucket via `update_hourly_steps`.
- Updates `GeckoCombinedSession` row (or creates one) for the time window.
- Updates `UserFriendLiveSeshPoints` (co-op scoreboard) only when the peer was present for this window.

Wrapped in `transaction.atomic()`.

The `points_pre_resolved=True` flag tells `process_gecko_data` to skip its own rule resolution and trust the amounts that `_build_pending_entry` already computed. This avoids double-resolving and means the gecko-helpers branch that re-derives `total_points` from rules is not exercised on the live path.

**Note on `UserLifetimeTotals`:** lifetime totals used to live on `GeckoScoreState` itself. They were split off so streak/energy writes (hot, frequent) don't share a row with monotonic counter writes (also frequent). `GeckoScoreState` may still carry the old `total_*` columns until a follow-up migration drops them — anything still reading them will be stale. Read from `UserLifetimeTotals` instead.

## Event award path (BE-initiated)

For discrete events that aren't gecko activity — e.g. creating a hello. Lives in `users/event_award_helpers.py:award_event_points(user, code, past_meet=None, friend_id=None)`.

What it does, inside one `transaction.atomic()`:

1. Looks up the `ScoreRule` for `code`. Unknown code → returns `None`, no write, no push.
2. Inserts a `GeckoPointsLedger` row with `multiplier=1`, `past_meet` set (if provided), `friend_id` set (if provided).
3. Bumps `UserLifetimeTotals.total_gecko_points`.
4. If `friend_id` is set, bumps `friends.GeckoData.total_points` for that (user, friend) row.
5. On commit, pushes `hello_points` event to the awarded user's socket(s) via `notify_user` (Channels + Rust transport).

What it explicitly does **not** do:

- No streak multiplier — events are always `multiplier=1`.
- No `UserFriendLiveSeshPoints` accrual — events never count toward the co-op gecko scoreboard, even if the hello's friend happens to be the user's current live-sesh partner.
- No `GeckoCombinedSession`, no hourly bucket, no `GeckoData` steps/distance/duration.
- No partner socket push — only the awarded user gets `hello_points`.

### Award sites today

| Source | Where | Notes |
|---|---|---|
| User-initiated hello | `friends/views.py:HelloCreate.perform_create` | Both sesh-cancelling and normal branch award |
| Sesh-invite-accept (sender) | `users/views.py:~1791` | Only if `sender_friend` exists |
| Sesh-invite-accept (recipient) | `users/views.py:~1799` | Only if `recipient_friend` exists |

The first PastMeet created on a new `Friend` (friends/models.py:225) intentionally does **not** award — it's history backfill at link time, not a real interaction.

### Socket event: `hello_points`

New event type, dedicated to event awards. FE adds a listener for it on top of everything it already listens for — existing `points_awarded` listeners are untouched. Payload:

```json
{
  "status": "ok",
  "awarded_user_id": <int>,
  "code": <int>,
  "label": <str>,
  "points": <int>,
  "multiplier": 1,
  "past_meet_id": <int|null>,
  "friend_id": <int|null>,
  "timestamp_earned": <iso8601>
}
```

Fires inside `transaction.on_commit` — never pushes for a rolled-back award.

### Why a separate path instead of routing through `process_gecko_data`

`process_gecko_data` carries baggage that's wrong for events: live-sesh scoreboard accrual, hourly step bucket, session row management, streak multiplier. Forcing events through it would require disabling each of those individually. A focused helper is cleaner.

## What is NOT happening

- The BE does not run any scheduled job that awards points.
- The BE does not detect activity from `steps` / `distance` and award gecko-activity points off them. Steps and distance are stored as raw counters; only `points_earned` entries produce ledger rows from the activity path.
- The Rust socket does not write to the DB.
- The Django Channels consumer at `/ws/gecko-energy/` is **dead** for the score path — the FE migrated to the Rust socket. The route in `users/routing.py` is still wired but no client connects to it.
- Event awards (hellos) are BE-initiated, so they're the exception to "no BE-initiated point awards" — but they're triggered by an explicit user-driven endpoint hit, not by a scheduler or detector.

## Where to read points totals (FE call patterns)

| Want | Endpoint | Source |
|---|---|---|
| User grand total (lifetime, all friends) | `GET /users/lifetime-totals/` | `UserLifetimeTotals.total_gecko_points` |
| Per-friend total (lifetime) | `GET /friends/<friend_id>/gecko/data/` | `GeckoData.total_points` |
| User points history (paginated) | `GET /users/gecko/points/all/ledger/?page=N` | `GeckoPointsLedger` rows for user |
| Per-friend points history (paginated) | `GET /users/gecko/points/friend/<friend_id>/ledger/?page=N` | `GeckoPointsLedger` filtered by friend |
| 24h step/sustenance seed | (existing 24h endpoint) | `GeckoHourlySteps` (Redis-cached) |

All read directly from denormalized counters — no `SUM(GeckoPointsLedger.amount)` on the read path. The ledger is the source of truth for backfill/audit/recovery, never for hot reads.

## The other points system (non-gecko)

There is a separate generic ledger that is unrelated to both gecko activity and event awards:

- `users.PointsLedger` (model)
- `AddPointsView` (users/views.py) — REST endpoint that uses `transaction.atomic()` + `F()` to credit `UserProfile.total_points` and write a ledger row.

When discussing "points" be specific about which system:

| System          | Model                | Triggered by | Surface                                  |
| --------------- | -------------------- | ------------ | ---------------------------------------- |
| Gecko activity  | `GeckoPointsLedger`  | FE event     | Rust socket → Django internal endpoint   |
| Event award     | `GeckoPointsLedger`  | BE view      | `award_event_points` inside view's atomic block |
| Generic points  | `PointsLedger`       | BE / REST    | `AddPointsView` and similar              |

Gecko activity and event award share the same ledger table — that's intentional, so per-user/per-friend totals and the points history view cover everything uniformly. The split is in the *write path*, not the storage.

## File map

| File                                                | Purpose                                                       |
| --------------------------------------------------- | ------------------------------------------------------------- |
| `gecko-socket-rust/src/main.rs`                     | Rust relay; proxies score actions to Django                   |
| `hellofriend/hfroot/users/views.py:1467`            | `gecko_socket_action` REST endpoint (Rust → Django entry)     |
| `hellofriend/hfroot/users/gecko_score_helpers.py`   | Gecko activity path: rule lookup, streak gating, persistence  |
| `hellofriend/hfroot/users/gecko_helpers.py`         | `process_gecko_data` — gecko activity cumulative/ledger writes |
| `hellofriend/hfroot/users/event_award_helpers.py`   | Event award path: `award_event_points`, code constants        |
| `hellofriend/hfroot/users/rust_push.py`             | `notify_user` — dual-transport (Channels + Rust) socket push  |
| `hellofriend/hfroot/friends/views.py:HelloCreate`   | User-initiated hello → invokes `award_event_points`           |
| `geckoscripts/models.py` (`ScoreRule`)              | Point values per event code (codes 1/2/3 today)               |
| `geckoscripts/management/commands/score_rules.txt`  | Running list of `create_score_rule` invocations               |
| `hellofriend/hfroot/users/models.py`                | `UserLifetimeTotals`, `GeckoScoreState`, `GeckoPointsLedger`  |
| `hellofriend/hfroot/friends/models.py`              | `GeckoData` (per-friend totals), `PastMeet` (hello row)       |
| `hellofriend/hfroot/users/management/commands/`     | `ensure_*`, `backfill_user_lifetime_totals`, `audit_user_signup_rows` |
| `hellofriend/hfroot/users/consumers.py`             | OLD path (`GeckoEnergyConsumer`) — dead from FE perspective   |

## ScoreRule codes (current)

Source of truth: `geckoscripts.ScoreRule` rows where `version=1`. Running list of `create_score_rule` commands lives in `geckoscripts/management/commands/score_rules.txt`.

| code | label                       | path           |
|------|-----------------------------|----------------|
| 1    | `GECKO_READ_ALL_NOTES`      | gecko activity |
| 2    | `CATEGORY_MATCHES_PREVIOUS` | gecko activity |
| 3    | `HELLO_CREATED`             | event award    |

To add a new code: pick the next integer, add a `create_score_rule` line to `score_rules.txt`, run it on each environment. For event awards, also add a constant (e.g. `HELLO_CREATED_CODE`) at the top of `event_award_helpers.py` and call `award_event_points(..., code=NEW_CODE, ...)` from the relevant view.
