# Gecko Collision / Proximity Games — Brainstorm

Notes on building proximity- and collision-based games once `main.rs` can
compare both geckos' coordinates server-side.

## Where things stand today

Both geckos' position frames already flow through the same `shared_room`
(`host_gecko_coords` and `guest_gecko_coords`), so the server *sees* both sides
right now. It just doesn't *look* at them — Rust currently treats each frame as
an opaque encoded blob and relays it (`broadcast_position_to_room`). It never
parses `[x, y]`. Making it collision-aware is a real but contained change, not a
rewrite.

## What it'd actually take

1. **Hold the latest position per client.** Today `PositionSlots` holds the
   *encoded outbound Message*, not parsed coords. Add a cheap parsed slot — e.g.
   `Mutex<Option<[f32; 2]>>` (or two `AtomicU32`s) hanging off the same `Arc` as
   `PositionSlots`, so you update it without taking the big `clients` write lock.
   We already parse the payload in `handle_update_host_gecko_position` to inject
   `from_user`/`friend_id`, so grabbing `position` there is nearly free.

2. **Compute proximity off a tick, not per-frame.** Don't run collision on every
   inbound frame from both sides — that's double work and frame-rate-dependent.
   Spawn one lightweight per-room task that wakes at a fixed rate (say 30Hz),
   reads both latest positions, and computes. Use **squared distance** (skip the
   `sqrt`) for all "are they close" checks — only need real distance for display.

3. **New event types for results** (never overload existing ones):
   `geckos_proximity` (continuous `{distance, closing_speed}`),
   `geckos_collided`, `gecko_entered_zone`, etc. FE adds listeners alongside the
   position ones.

4. **The honest caveat: tunneling.** The coalescing slots *drop* intermediate
   positions by design (newest wins). For proximity that's fine — only care
   where they are now. But for fast "did they actually touch" collision, two
   geckos can pass through each other between ticks and you'd miss it. For tight
   collision, do **swept collision**: check the segment from
   `prev_pos → current_pos` against the other gecko, not just the two points.
   That's the difference between "feels cheap" and "feels real."

None of this violates the DB boundary — collision math is pure CPU, no `sqlx`.
Anything *authoritative* (awarding the win/points) still round-trips to Django
exactly like `request_points` and `propose_gecko_win` do today.

## Games that fit the existing primitives

The world already has a shape: **host hides moments, guest digs them up, host's
gecko warns ("they're digging up our moment!", "MOMENT STOLEN!")**. It's already
a tug-of-war over moments. Proximity makes that physical instead of abstract.

### Proximity / distance-driven
- **Hot & cold dig** — guest doesn't see buried moments, but their gecko's
  emotion/color intensifies (reuse `peer_gecko_emotion`) as they near a host
  moment's coords. The host watches the guest close in and fires the existing
  `LosingWarning` ladder (Huh → Digging → Losing → Stolen) based on the *real*
  server-measured distance instead of guessing.
- **Keep-away / shielding** — host steers their gecko to physically interpose
  between the guest and a moment. Distance-to-moment vs guest's distance decides
  if it gets stolen. Pure server geometry.
- **Tether** — the two geckos must stay within a radius to charge something (a
  shared capsule's progress). Drift apart and `capsule_progress` decays. We
  already broadcast capsule progress.

### Collision / contact-driven
- **Tag / steal-on-touch** — contact transfers a held moment (`held_moments` is
  already in the host frame!). Swept collision matters here.
- **Bump-to-gift** — touch to hand a moment over deliberately; a cooperative
  inverse of stealing.
- **Sumo** — collisions impart knockback; push your partner's gecko off a zone.
  Server computes the bump vector.

### Zone / region-driven (cheapest to ship first)
- **Capture-the-moment zones** — moments define circular regions;
  `gecko_entered_zone` fires when a gecko's coords cross in. No swept math
  needed, just point-in-circle per tick. Lowest-risk first step, reuses
  everything.
- **Race to a moment** — first gecko to a target coord wins; server declares it,
  Django records the win.

## Suggested first step

Build **zone-entry first** — it's point-in-circle on a tick, needs only the
parsed-position slot and one new event type, and it proves out the whole
"server measures geometry → emits new event → Django scores it" pipeline before
taking on swept collision.
