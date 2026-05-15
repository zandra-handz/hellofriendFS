# Gecko Score System

How points get from the React Native client to the database.

## End-to-end flow

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

- Increments `GeckoData.total_steps`, `total_distance`, `total_duration`, `total_points` via `F()` expressions (atomic).
- Increments `GeckoScoreState.total_steps`, `total_distance`, `total_duration`, `total_gecko_points` via `F()` expressions.
- Bulk-creates `GeckoPointsLedger` rows for each resolved point entry.
- Updates hourly bucket via `update_hourly_steps`.
- Updates `GeckoCombinedSession` row (or creates one) for the time window.

Wrapped in `transaction.atomic()`.

The `points_pre_resolved=True` flag tells `process_gecko_data` to skip its own rule resolution and trust the amounts that `_build_pending_entry` already computed. This avoids double-resolving and means the gecko-helpers branch that re-derives `total_points` from rules is not exercised on the live path.

## What is NOT happening

- The BE does not run any scheduled job that awards points.
- The BE does not detect activity from `steps` / `distance` and award points off them. Steps and distance are stored as raw counters; only `points_earned` entries produce ledger rows.
- The Rust socket does not write to the DB.
- The Django Channels consumer at `/ws/gecko-energy/` is **dead** for the score path — the FE migrated to the Rust socket. The route in `users/routing.py` is still wired but no client connects to it.

## The other points system (non-gecko)

There is a separate generic ledger that is unrelated to the gecko system:

- `users.PointsLedger` (model)
- `AddPointsView` (users/views.py:725) — REST endpoint that uses `transaction.atomic()` + `F()` to credit `UserProfile.total_points` and write a ledger row.
- This system **is** BE-initiated. Endpoints award points directly without an FE event.

When discussing "points" be specific about which system:

| System          | Model                | Triggered by | Surface                                  |
| --------------- | -------------------- | ------------ | ---------------------------------------- |
| Gecko points    | `GeckoPointsLedger`  | FE event     | Rust socket → Django internal endpoint   |
| Generic points  | `PointsLedger`       | BE / REST    | `AddPointsView` and similar              |

## File map

| File                                                | Purpose                                                       |
| --------------------------------------------------- | ------------------------------------------------------------- |
| `gecko-socket-rust/src/main.rs`                     | Rust relay; proxies score actions to Django                   |
| `hellofriend/hfroot/users/views.py:1467`            | `gecko_socket_action` REST endpoint (Rust → Django entry)     |
| `hellofriend/hfroot/users/gecko_score_helpers.py`   | Live score path: rule lookup, streak gating, persistence      |
| `hellofriend/hfroot/users/gecko_helpers.py`         | `process_gecko_data` — the actual cumulative/ledger writes    |
| `geckoscripts/models.py` (`ScoreRule`)              | Point values per event code                                   |
| `hellofriend/hfroot/users/models.py`                | `GeckoScoreState`, `GeckoData`, `GeckoPointsLedger`           |
| `hellofriend/hfroot/users/consumers.py`             | OLD path (`GeckoEnergyConsumer`) — dead from FE perspective   |
