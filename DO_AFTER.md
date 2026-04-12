# DO AFTER — Live Sesh gecko coord sharing

Goal: when a live sesh is active between User A (host) and User B (guest), both users
should be able to see each other's gecko screen positions in real time. Each user
already broadcasts their own position to their own group
`gecko_shared_with_friend_{self.user.id}`. The missing piece is: during a live sesh,
each user must also JOIN the partner's group to receive the partner's broadcasts.

No new group is created. No central "session channel." Just cross-subscription to
existing per-user groups for the duration of the session.

---

## Backend — `users/consumers.py` (GeckoEnergyConsumer)

### 1. On connect — auto-rejoin if a session is already active
After the existing `group_add` for the user's own `shared_with_friend` group,
query `UserFriendCurrentLiveSesh` for `self.user`. If one exists and
`expires_at > timezone.now()`:

- Build `partner_group = f'gecko_shared_with_friend_{sesh.other_user_id}'`
- `await self.channel_layer.group_add(partner_group, self.channel_name)`
- Store on `self.joined_sesh_group = partner_group` (for disconnect cleanup)

This handles reconnects / app restarts mid-session with no client involvement.

### 2. New `receive()` action — `join_live_sesh`
Client sends `{"action": "join_live_sesh"}` when a session becomes active mid-connection
(e.g. right after accepting an invite, or after being notified via the notifications socket).

Consumer logic:
- Look up the user's current sesh in DB.
- If missing or expired → do nothing (or send back a `{"action": "join_live_sesh_failed"}`).
- If valid, do the same `group_add` as on-connect and store `self.joined_sesh_group`.
- Optionally send `{"action": "join_live_sesh_ok"}` back.

### 3. New `receive()` action — `leave_live_sesh`
For explicit early-leave (user closes session screen, etc.):
- `group_discard(self.joined_sesh_group, self.channel_name)` if set
- Clear `self.joined_sesh_group`

### 4. On disconnect
If `self.joined_sesh_group` is set, `group_discard` it too (in addition to the
existing discards).

### 5. DB helper
Use `@database_sync_to_async` for the session lookup — same pattern as existing
DB helpers in the consumer:

```python
@database_sync_to_async
def _get_active_partner_id(self):
    from users.models import UserFriendCurrentLiveSesh
    sesh = UserFriendCurrentLiveSesh.objects.filter(
        user_id=self.user.id,
        expires_at__gt=timezone.now(),
    ).first()
    return sesh.other_user_id if sesh else None
```

---

## Frontend — `useGeckoEnergySocket` hook

### 1. Expose a new sender
```ts
const joinLiveSesh = useCallback(() => {
  if (wsRef.current?.readyState === WebSocket.OPEN) {
    wsRef.current.send(JSON.stringify({ action: "join_live_sesh" }));
  }
}, []);

const leaveLiveSesh = useCallback(() => {
  if (wsRef.current?.readyState === WebSocket.OPEN) {
    wsRef.current.send(JSON.stringify({ action: "leave_live_sesh" }));
  }
}, []);
```

Add to the hook's return.

### 2. Trigger `joinLiveSesh` when:
- A `live_sesh_invite_accepted` notification arrives (sender's side)
- An invite accept REST call succeeds (recipient's side)

### 3. Trigger `leaveLiveSesh` when the user exits the session UI.

---

## Security notes

- Never accept a client-provided user id / group name. Always derive from
  `self.user` + DB state.
- Every `group_add` must be preceded by a DB check that the user is in an
  active, unexpired session.
- The partner's group name is fine to construct server-side (it's just an
  implementation detail), but the partner's identity comes from the sesh row,
  not from client input.
