# Gecko Energy System

## Overview

Energy is a 0.0–1.0 value (with optional surplus up to 2.0) that drains from walking (steps) and recharges from rest. The **frontend is the source of all data**: steps, session start/end times, distance, and streak activations all originate on the device. The backend receives this data, stores it, and runs the authoritative energy computation. The frontend mirrors that computation between syncs for a responsive UI.

---

## Backend Computation

### Model: `GeckoScoreState` (users/models.py:426)

| Field              | Type     | Default        |
|--------------------|----------|----------------|
| energy             | Float    | 1.0            |
| surplus_energy     | Float    | 0.0            |
| energy_updated_at  | DateTime | now            |
| revives_at         | DateTime | null           |
| multiplier         | Int      | 1              |
| base_multiplier    | Int      | 1              |
| expires_at         | DateTime | now            |

### Constants (users/constants.py)

| Constant                   | Value        |
|----------------------------|--------------|
| STEPS_TO_FULL_DRAIN        | 100,000      |
| STEP_FATIGUE_PER_STEP      | 1/100,000    |
| STREAK_FATIGUE_MULTIPLIER  | 0.25         |
| SURPLUS_CAP                | 2.0          |

### Derived values (computed at runtime, not stored)

| Value                      | Formula                               | Source           |
|----------------------------|---------------------------------------|------------------|
| recharge_per_second        | 1 / (full_rest_hours * 3600)          | GeckoConfigs     |
| streak_recharge_per_second | recharge_per_second * 0.5             | GeckoConfigs     |
| stamina                    | GeckoConfigs.stamina (default 1.0)    | GeckoConfigs     |
| revival_seconds            | GeckoConfigs.max_duration_till_revival (default 60) | GeckoConfigs |
| full_rest_hours            | 24 - max_active_hours                 | GeckoConfigs     |

### `recompute_energy()` (users/models.py:445)

Called whenever energy needs to be recalculated. Runs as a batch over the time since `energy_updated_at`.

**Step-by-step:**

1. `elapsed = now - energy_updated_at` (seconds)
2. If `elapsed <= 0`, return.
3. **Dead check**: if `energy <= 0` and `surplus_energy <= 0`:
   - If `revives_at` exists and `now >= revives_at`: set `energy = 0.05`, clear `revives_at`.
   - If no `revives_at`: set `revives_at = now + revival_seconds`.
   - Save and return.
4. **Query sessions**: `GeckoCombinedSession` where `ended_on > energy_updated_at`.
5. **Sum steps**: `new_steps = sum(session.steps for all matching sessions)`.
6. **Sum active time**: `active_seconds = sum(session.ended_on - session.started_on for all matching sessions)`.
7. `rest_seconds = max(0, elapsed - active_seconds)`.
8. **Streak check**: `streak_is_active = multiplier > base_multiplier AND expires_at > energy_updated_at`.
9. **If streak is active and active_seconds > 0**:
   - `streak_end = min(expires_at, now)`
   - `streak_seconds = streak_end - energy_updated_at` (seconds)
   - `streak_ratio = min(1.0, streak_seconds / elapsed)`
   - `streak_active_seconds = active_seconds * streak_ratio`
   - `streak_steps = new_steps * (streak_active_seconds / active_seconds)`
   - `normal_steps = new_steps - streak_steps`
   - `fatigue = normal_steps * STEP_FATIGUE_PER_STEP + streak_steps * STEP_FATIGUE_PER_STEP * STREAK_FATIGUE_MULTIPLIER`
   - `recharge = rest_seconds * recharge_per_second + streak_active_seconds * streak_recharge_per_second`
10. **If no streak**:
    - `fatigue = new_steps * STEP_FATIGUE_PER_STEP`
    - `recharge = rest_seconds * recharge_per_second`
11. `effective_recharge = recharge * stamina`
12. `effective_fatigue = fatigue / stamina`
13. `net = effective_recharge - effective_fatigue`
14. **Apply net**:
    - If `net >= 0`: fill energy up to 1.0, overflow goes to surplus (capped at SURPLUS_CAP).
    - If `net < 0`: drain surplus first, then energy. Floor at 0.
15. **Revival bookkeeping**: if energy and surplus both hit 0, set `revives_at` if not already set. Otherwise clear it.
16. Set `energy_updated_at = now`, save.

---

## What triggers `recompute_energy()`

| Trigger | Location | When |
|---------|----------|------|
| `GeckoCombinedSession.save()` | users/models.py:804 | Every time a session is created or updated (i.e., every `update_gecko_data` call that includes session times) |
| `GeckoScoreStateView.get_object()` | users/views.py:353 | Every GET request for score state |
| `GeckoScoreStateView.update()` | users/views.py:401 | Every PUT/PATCH to score state (streak activation) |
| `GeckoConfigs.save()` | users/models.py:671 | When gecko configs change |
| `GeckoConfigsSerializer.validate()` | users/serializers.py:149 | When validating active_hours changes |

---

## The Sync Call: `update_gecko_data` (friends/views.py:272)

**Endpoint**: POST to update gecko data for a friend.

**Frontend sends** (the frontend is the sole source of all this data — the backend has no independent way to measure steps, distance, or session timing):
- `steps` — delta steps since last call
- `distance` — delta distance since last call
- `started_on` — session start (ISO-8601)
- `ended_on` — session end (ISO-8601)
- `points_earned` — list of `{code, label, timestamp_earned}`

**What the backend does**:

1. Resolves points against ScoreRules, applies multiplier based on whether each point's timestamp falls before `expires_at`.
2. Updates `GeckoData` and `GeckoCombinedData` totals (steps, distance, duration, points) using `F()` expressions.
3. **Session handling**:
   - Looks for an existing `GeckoCombinedSession` where `started_on <= new_started_on` AND `ended_on >= new_started_on` (overlapping).
   - **If found (merge)**: extends `ended_on` to `new_ended_on`, adds `delta_steps` to `session.steps`, adds `delta_distance`, adds points.
   - **If not found**: creates a new session record.
   - Same logic for `GeckoDataSession` (per-friend).
4. `GeckoCombinedSession.save()` triggers `recompute_energy()`.
5. Returns serialized `GeckoData` (NOT the score state).

**Key detail about session merging**: Because the frontend sends the same `started_on` each interval (the session start doesn't change), every sync during a session will match the existing session and merge into it. The session's `steps` field accumulates all delta_steps across syncs. The session's `ended_on` extends forward each time.

---

## What the frontend receives (GeckoScoreState serializer)

From `GeckoScoreStateSerializer` (users/serializers.py:50):

| Field                      | Source                     |
|----------------------------|----------------------------|
| multiplier                 | model field                |
| base_multiplier            | model field (read-only)    |
| expires_at                 | model field                |
| energy                     | model field (read-only)    |
| surplus_energy             | model field (read-only)    |
| energy_updated_at          | model field (read-only)    |
| revives_at                 | model field (read-only)    |
| recharge_per_second        | computed: `1 / (full_rest_hours * 3600)` |
| streak_recharge_per_second | computed: `recharge_per_second * 0.5` |
| step_fatigue_per_step      | constant: `1/100000`       |
| streak_fatigue_multiplier  | constant: `0.25`           |
| surplus_cap                | constant: `2.0`            |

**Note**: `stamina` is on `GeckoConfigs`, NOT on this serializer. It's in the `GeckoConfigsSerializer` `read_only_fields` but NOT in its `fields` list — so it is **not currently sent to the frontend**. The backend uses `stamina` (default 1.0) in `recompute_energy`, but the frontend would need to get it from somewhere if stamina != 1.0.

---

## Full Flow: What Happens From App Open to Walking

### 1. App opens after days of inactivity

The user hasn't opened the app in days. The backend still has the old `energy_updated_at` from the last session. Energy has not been recomputed yet — the backend only computes on demand, not on a timer.

The frontend mounts the gecko screen and fetches `GeckoScoreState` (GET request). This GET triggers `recompute_energy()` on the backend. The backend looks at how much time has passed since `energy_updated_at`, finds no sessions in that gap (the user wasn't walking), treats all that time as rest, and recharges energy accordingly. It sets `energy_updated_at = now` and saves. The frontend receives the fresh energy value and the new `energy_updated_at`.

At this point, the frontend knows the correct energy and knows that `energy_updated_at` is essentially "just now." The gait class is initialized with these values.

### 2. The user starts walking

The frontend starts its animation loop (`requestAnimationFrame`). Every frame, the gait class runs `update()`, which calls `_recomputeEnergy()`.

The frontend is the source of all step data. Steps are counted locally by the gait animation — each walking cycle triggers `stepCompleted()` which increments the step counter. The backend has no pedometer or sensor; it only knows about steps when the frontend tells it.

The frontend is also the source of session timing. It records when the session started (`sessionStartMs`) and updates the current time (`sessionEndMs`) every frame. The backend only learns about session timing when the frontend sends it.

Streaks are also driven by the frontend. The user activates a streak on the device, which sends a PUT/PATCH to `GeckoScoreState` to set the multiplier and expiration time.

### 3. Frontend computes energy every frame

Each frame, `_recomputeEnergy()` runs using the same formula as the backend:

- It starts from the snapshot values received from the backend (energy, surplus, energy_updated_at).
- It computes how much time has passed since `energy_updated_at`.
- It figures out how much of that time was active (the user was in a session) and how much was rest.
- It counts how many steps have been taken since the snapshot baseline.
- If a streak is active, it splits the steps and time into streak vs non-streak portions using the same ratio logic as the backend.
- It computes fatigue (from steps) and recharge (from rest time and streak active time), applies stamina, and gets the net change.
- It applies that net change to the snapshot energy/surplus values.

This gives the user a smooth, real-time energy display that updates every frame. The energy bar moves as they walk.

### 4. Every 60 seconds: sync with backend

A timer fires `handleUpdateGeckoDataState`. This sends the backend:
- The number of new steps since the last sync (delta, not total).
- The session start time (same every sync within a session) and the current end time.
- Distance covered since last sync.
- Any points earned since last sync.

The backend receives this and does the following:
1. Adds the delta steps/distance/duration to the running totals (`GeckoData`, `GeckoCombinedData`).
2. Looks for an existing `GeckoCombinedSession` that overlaps with the sent time range. Since the frontend sends the same `started_on` every time (the session hasn't ended), it always finds the session created on the first sync. It extends that session's `ended_on` to the new value and adds the delta steps to the session's step total.
3. Saving the session triggers `recompute_energy()`. The backend looks at the time since its last `energy_updated_at`, finds the session (whose `ended_on` is after `energy_updated_at`), sums up the session's total steps, computes active/rest time, and recalculates energy. It saves and sets `energy_updated_at = now`.

After this, the frontend fetches the updated `GeckoScoreState` (GET). The GET triggers another `recompute_energy()`, but since `energy_updated_at` was just set moments ago, `elapsed` is near zero and nothing changes. The frontend receives the authoritative energy value and calls `syncFromBackend()` on the gait class, which overwrites the snapshot with the backend's values. The local accumulators reset, and the per-frame computation starts fresh from the new snapshot.

### 5. Streak activation mid-session

If the user activates a streak, the frontend sends a PUT/PATCH to `GeckoScoreState` with the new multiplier and expiration time. The backend saves this and runs `recompute_energy()`. The frontend receives the updated score state and syncs.

The streak changes how energy is computed: during the streak period, steps cause only 25% of normal fatigue (multiplied by `STREAK_FATIGUE_MULTIPLIER = 0.25`), and active time generates recharge at `streak_recharge_per_second` (half the rest recharge rate). This means walking during a streak drains energy much more slowly.

### 6. Session ends

When the user leaves the gecko screen, the session ends. No more frames run, no more steps are counted, no more syncs fire. The backend's `energy_updated_at` reflects the last sync. The next time the app opens (step 1 again), the backend will treat all the time since then as rest and recharge accordingly.

---

## Frontend Energy Computation (detail)

The frontend mirrors `recompute_energy()` in `gaitClass.js` using values from the score state serializer. It runs every frame to keep the energy display responsive between 60-second syncs.

### Data the frontend has locally

The frontend is the original source of all of this data. It generates the steps, tracks the session, and sends everything to the backend.

- **Steps**: counted locally per-frame via gait animation. The backend only knows about steps after the frontend sends them.
- **Session timing**: `sessionStartMs` (when the session began) and `sessionEndMs` (updated every frame to `Date.now()`). The backend only knows about session timing after the frontend sends it.
- **Snapshot values**: `energy`, `surplus_energy`, `energy_updated_at` — last received from backend via GeckoScoreState GET. These are the starting point for each frame's computation.
- **Config values**: `recharge_per_second`, `streak_recharge_per_second`, `step_fatigue_per_step`, `streak_fatigue_multiplier`, `surplus_cap`, `multiplier`, `base_multiplier`, `expires_at`, `stamina` (from GeckoConfigs).

### Frontend recompute (per frame)

Uses the same formula as the backend:
1. `elapsed = now - energy_updated_at`
2. Compute `active_seconds` and `rest_seconds` from the local session.
3. Compute steps since snapshot baseline.
4. Apply streak logic (same ratios as backend).
5. Compute fatigue, recharge, net, apply to snapshot energy/surplus.

### Sync cycle

1. **Every 60 seconds**: `handleUpdateGeckoDataState` fires.
   - Sends delta steps, session start/end, distance, points to `update_gecko_data`.
   - Backend merges into session, triggers `recompute_energy`, saves.
   - Frontend then fetches updated `GeckoScoreState` (GET).
   - `syncFromBackend()` overwrites the snapshot with authoritative backend values.
   - Resets local accumulators.

2. **On streak activation**: `GeckoScoreState` is updated (PUT/PATCH), which also triggers `recompute_energy`. Frontend receives new score state and syncs.

3. **Between syncs**: frontend runs `_recomputeEnergy()` every frame using snapshot + local accumulation. This gives a smooth, responsive energy display that closely tracks what the backend will compute at next sync.

---

## Known considerations

- **Timing gap**: The backend's `now` when it runs `recompute_energy` is always slightly later than the frontend's last frame (due to network latency). This means the backend sees slightly more elapsed time, slightly more rest seconds, and computes a slightly higher energy value. This is an inherent difference that the 60-second sync corrects.
- **Session merging**: The backend's `GeckoCombinedSession.steps` is the total accumulated steps for the entire merged session, not a delta. Each sync adds delta_steps on top of the previous total. When `recompute_energy` runs, it queries sessions where `ended_on > energy_updated_at` and sums their full step counts. This works correctly because `energy_updated_at` is updated after each computation — the next time `recompute_energy` runs, it only picks up the session again if `ended_on` was extended (meaning a new sync arrived with new steps added to the total).
- **Stamina**: The backend uses `stamina` from `GeckoConfigs` (default 1.0) to scale recharge up and fatigue down. This value is currently not included in the `GeckoConfigsSerializer` fields list, so if stamina is ever changed from 1.0, the frontend won't know about it and the computations will diverge.
