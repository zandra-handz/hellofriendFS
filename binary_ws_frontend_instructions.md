# Instructions for frontend Claude: Convert gecko-position WebSocket traffic to binary

Convert the gecko-position WebSocket traffic in the hook (the one returning `sendGuestGeckoPosition`, `sendHostGeckoPosition`, `registerOnHostGeckoCoords`, `registerOnGuestGeckoCoords`, `registerOnGeckoCoords`, `wsRef`, `sendRaw`) from JSON to binary frames. Leave every other message type (`score_state`, `sync`, `join_live_sesh_ok`, `leave_live_sesh_ok`, `flush_ack`, `live_sesh_cancelled`, etc.) as JSON — they stay untouched.

## Wire format (little-endian, Int16 fixed-point ×10)

One byte message-type tag at offset 0, then Int16 values starting at offset 2 (byte 1 is padding for alignment).

- **Tag 1 — host gecko** (22 bytes + moments): `pos.x, pos.y, s0.x, s0.y, s1.x, s1.y, s2.x, s2.y, s3.x, s3.y` → 10 Int16s. Moments: append a length-prefixed block at offset 22 — Uint8 count, then `count × 2` Int16s for (x,y). If moments are fixed-count, treat them like steps.
- **Tag 2 — guest gecko** (22 bytes): same as host but no moments. 10 Int16s: position + 4 steps.
- **Tag 3 — plain gecko** (6 bytes): position only, 2 Int16s.

All coordinates are multiplied by 10 before encoding and divided by 10 on decode (1-decimal precision). Round with `Math.round`.

## Changes to make

### 1. On socket open
Set `wsRef.current.binaryType = 'arraybuffer'` immediately after creating the WebSocket.

### 2. `sendHostGeckoPosition(position, steps, moments, force)`
Replace the JSON `ws.send(JSON.stringify({action:'update_host_gecko_position', data:{...}}))` with:

```ts
const count = moments?.length ?? 0;
const buf = new ArrayBuffer(22 + 1 + count * 4);
const v = new DataView(buf);
v.setUint8(0, 1);                                      // tag
v.setInt16(2, Math.round(position[0] * 10), true);
v.setInt16(4, Math.round(position[1] * 10), true);
for (let i = 0; i < 4; i++) {
  v.setInt16(6 + i*4, Math.round(steps[i][0] * 10), true);
  v.setInt16(8 + i*4, Math.round(steps[i][1] * 10), true);
}
v.setUint8(22, count);
for (let i = 0; i < count; i++) {
  v.setInt16(23 + i*4, Math.round(moments[i][0] * 10), true);
  v.setInt16(25 + i*4, Math.round(moments[i][1] * 10), true);
}
wsRef.current.send(buf);
```

### 3. `sendGuestGeckoPosition(position, steps, force)`
Same shape as host but tag `2`, no moments block (fixed 22 bytes).

### 4. `sendGeckoPosition(position, force)` (the plain one)
Tag `3`, 6 bytes: just position.

### 5. Throttle + skip-if-unchanged (keep or add)
Before building the buffer, skip the send if `position` and `steps`/`moments` are unchanged from the last send, and rate-limit to 30Hz unless `force` is true. Store last-sent values in refs.

### 6. `ws.onmessage` dispatcher
At the top of the handler, branch on data type:

```ts
if (event.data instanceof ArrayBuffer) {
  const v = new DataView(event.data);
  const tag = v.getUint8(0);
  const readPos = (off: number): [number, number] =>
    [v.getInt16(off, true) / 10, v.getInt16(off + 2, true) / 10];
  const readSteps = (off: number): [number, number][] =>
    [0,1,2,3].map(i => readPos(off + i*4));

  if (tag === 1) {
    const position = readPos(2);
    const steps = readSteps(6);
    const count = v.getUint8(22);
    const moments: [number, number][] = [];
    for (let i = 0; i < count; i++) moments.push(readPos(23 + i*4));
    onHostGeckoCoordsRef.current?.({ position, steps, moments });
  } else if (tag === 2) {
    onGuestGeckoCoordsRef.current?.({ position: readPos(2), steps: readSteps(6) });
  } else if (tag === 3) {
    onGeckoCoordsRef.current?.({ position: readPos(2) });
  }
  return;
}

// existing JSON path below (unchanged)
const msg = JSON.parse(event.data);
// switch on msg.action ...
```

The `registerOnHostGeckoCoords` / `registerOnGuestGeckoCoords` / `registerOnGeckoCoords` callbacks now receive plain objects (`{position, steps, moments?}`) instead of raw JSON fields — update any consumers that assumed a `from_user` field if they need it (if they do, add a Uint32 after the tag; if not, omit).

### 7. `sendRaw`
Leave as-is for JSON callers. If any gecko-position caller currently goes through `sendRaw` with a JSON object, reroute it through the new typed functions.

### 8. Shared Values (`peerGeckoPositionSV`, `hostPeerGeckoPositionSV`, `guestPeerGeckoPositionSV`)
Update wherever they're written from incoming coords to use the decoded `{position, steps, moments}` objects from the binary path.

## Backend contract
The Django Channels consumer:
- Accepts both `text_data` (JSON) and `bytes_data` (binary).
- On binary receive: peeks byte 0 to identify host/guest/plain, enforces `is_host` gating, then forwards the **raw bytes unchanged** through the channel layer group. No re-encoding.
- Broadcast handlers call `self.send(bytes_data=payload)`.

Do not send a `from_user` in the binary frame — the backend does not add one (to keep forwarding zero-copy). If clients need it, tell backend Claude to prepend a 4-byte `from_user` after the tag, and adjust offsets here (+4) accordingly.

## Security / validation
Binary over `wss://` is just as secure as JSON — TLS encrypts the bytes the same way. The real risk is app-layer parsing. Defensive checks:
- Validate `buf.byteLength` against the expected size for each tag before decoding.
- Clamp the moments `count` byte (reject if `count > MAX` or if `len != 23 + count*4`).
- Keep server-side `is_host` gating before forwarding.

## Do not change
- JSON messages for score state, sync, session control, flush, energy updates.
- The `action` string switch for JSON — keep it intact for the non-gecko paths.
- Public return shape of the hook.

## Verify
After changes: open the session, confirm host frames arrive at guest and vice versa, confirm position/steps/moments render identically to the JSON version within 0.1 precision, and confirm non-gecko actions (score state, join/leave) still work.
