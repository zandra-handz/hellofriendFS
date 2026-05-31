# Gecko Live-Sesh Moment Sync — Working Notes

Reference doc so we don't lose context if the machine crashes. Last updated: 2026-05-30.

---

## Repos / where things live

- **Backend + Rust socket:** `hellofriendFS` (this working dir). Django + `gecko-socket-rust/src/main.rs`.
- **Frontend (React Native):** sibling repo `hellofriendRN` (NOT inside hellofriendFS). The `@/` import alias resolves there.

### Key files
| Role | File |
|------|------|
| Rust WS relay | `hellofriendFS/gecko-socket-rust/src/main.rs` |
| Socket context (FE) | `hellofriendRN/src/context/GeckoWebsocketContext.tsx` |
| HOST screen | `hellofriendRN/app/screens/fidget/ScreenGecko.tsx` |
| HOST engine wrapper | `hellofriendRN/app/assets/shader_animations/MomentsSkia.tsx` |
| HOST moment class | `hellofriendRN/app/assets/shader_animations/momentsClass.js` |
| GUEST screen | `hellofriendRN/app/screens/fidget/ScreenSecretGecko.tsx` |
| GUEST engine wrapper | `hellofriendRN/app/assets/shader_animations/MirrorPlayGecko.tsx` |
| GUEST moment class | `hellofriendRN/app/assets/shader_animations/momentsMirrorClass.js` |

NOTE: ignore `BraveGeckoSkia`, `MomentsSkiaCur/Old`, `MirrorPlayGecko` variants, `comparee`, etc. — not in scope.

---

## The big picture / design principle

Each moment is one record keyed by `id`, with **field-level ownership**:
- **HOST owns layout:** `coord`, `stored_index`, set membership (add/remove/reshuffle).
- **GUEST owns `guest_progress`** (intended as a catch-all for any future guest-side mutation of a moment).

Each inbound socket message patches **only the fields its owner controls**, so host resends can't clobber guest progress and vice versa (disjoint owners = no merge conflict by construction).

### Channels
- `all_host_capsules` — **reliable** (Rust ordered mpsc / `broadcast_to_room_with_clients`). Full board snapshot. Used on connect/presence AND now on reshuffle.
- `host_gecko_coords` — **lossy/coalesced** (Rust PositionSlots, latest-wins, can drop). Pure gecko pose + per-frame coords for the slide. Historically also smuggled the `moments` array (the bug source).
- `capsule_progress` — **reliable**, guest→host, carries `guest_progress`.

### Why bugs happened
- Continuous deltas (drag) tolerate the lossy channel (self-healing: next frame catches up).
- **One-shot** full-board changes (reshuffle) do NOT — if the single frame coalesces away, guest stays stale until next full dump. Plus FE throttle (`GECKO_POSITION_THROTTLE_MS` 50ms) + `flushDirty()` clearing the dirty set even when the send is skipped → reshuffle eaten.
- Progress override: host packed moments into a `Float32Array`, so `guest_progress` column was always a number (never null), so the guest's field-preserving merge never preserved — every host frame reset the guest's live progress.

---

## DONE (shipped to FE this session, first pass)

### Fix 1 — progress override (guest = sole authority for guest_progress)
- `GeckoWebsocketContext.tsx` ~L1237 (`host_gecko_coords` pack): `momentsScratch[i][4] = -1;` (sentinel "host has no opinion")
- `GeckoWebsocketContext.tsx` ~L1297 (`all_host_capsules` pack): `momentsScratch[i][4] = -1;`
- `MirrorPlayGecko.tsx` `applyMirrorMomentsDelta`: guest_progress branch now requires `incomingProgress !== -1` to apply incoming; otherwise preserves existing.
  - ONE guard covers BOTH inbound host paths (`hostCapsulesSV` and `hostPeerGeckoPositionSV.value.moments` both funnel through `applyMirrorMomentsDelta`).
  - `stored_index` (`[i][3]`) left untouched — `-1` legitimately means "not held" there. Sentinel is guest_progress-only.

### Fix 2 — reshuffle drops (animate/slide + durable)
- `ScreenGecko.tsx`: added `useEffect` keyed on `scatteredMoments` (right after the `partner_reconnected` effect):
  - Fires after the React state commit, so `moments.current` has ingested new coords (no stale-coord broadcast).
  - Calls `triggerSendAllHostCapsulesRef.current?.()` — builds snapshot from live `moments.current` (correct source), sends on reliable `all_host_capsules`.
  - Host-only; `didInitialScatterRef` skips the first commit so the initial dump isn't double-sent.
  - `host_gecko_coords` per-frame stream still drives the visual slide; `all_host_capsules` carries the guaranteed final layout.

---

## TO VERIFY (manual test — not done yet)
1. **Progress holds through reshuffle:** guest digs a moment to ~50, host moves/reshuffles → guest progress should NOT snap to 0.
2. **Reshuffle lands mid-motion:** host reshuffles while gecko is moving → guest converges to new layout (the original drop bug).

## WATCH-ITEM (only if a test fails)
- The `scatteredMoments` effect reads live `moments.current`. It relies on MomentsSkia's `[momentsData,...]` ingest effect running before ScreenGecko's effect reads it. If reshuffle ever sends **one layout behind**, move the trigger INTO MomentsSkia's `[momentsData]` ingest effect instead.
- `didInitialScatterRef` skips the first non-empty commit. Safe unless `scatteredMoments` is ever reset to initial WITHOUT a connect/presence dump (that path doesn't appear to exist).

---

## NOT YET BUILT (follow-ups, optional)
- **Dedicated `host_capsules_coord_changes` event** — a reliable, per-moment delta channel for committed host layout changes (drag-commit, pickup/drop via stored_index, add/remove), so `host_gecko_coords` can eventually carry ZERO board data (pose only). Stub listener already exists in GeckoWebsocketContext. This generalizes Fix 2; current approach (resend full `all_host_capsules` on reshuffle) is the simpler version and is sufficient for now.
- **Session cache (Redis) of the unified moment record** — optional resilience for reconnect; NOT the fix for any current bug. If added, cache the unified record, not a separate locations blob.
- **Host as live source of truth on reconnect** — already works: guest reconnect → `partner_reconnected` → host resends in-memory layout. Backend persistence stays lazy / cold-start fallback only. Do NOT switch to backend-push of layout (would serve stale coords if a reshuffle hasn't persisted yet).

---

## Constraints / project rules to respect
- Never edit Django models/migrations directly — propose in chat.
- Rust WS must NOT touch the DB directly — all DB work goes through Django.
- New socket pushes get NEW event types — never overload an existing `event_type` / action string; FE adds a new listener alongside existing ones.
- Lead with the most performant option.
