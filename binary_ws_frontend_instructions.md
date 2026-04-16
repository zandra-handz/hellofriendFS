# Instructions for frontend Claude: Add msgpack to gecko-position WebSocket traffic

The backend now accepts **both JSON (text frames) and msgpack (binary frames)** and will respond with msgpack for gecko coord broadcasts. Convert the three gecko-position senders to msgpack. All other messages (score_state, sync, join/leave, flush, energy) stay JSON — do not touch them.

## What is msgpack?
Same keys, same objects, same structure as JSON — just a more compact binary serialization. No manual byte packing, no offset math.

## Install
```bash
npm install @msgpack/msgpack
```
Import: `import { encode, decode } from '@msgpack/msgpack';`

## Changes to make

### 1. On socket open
Set `ws.binaryType = 'arraybuffer'` immediately after creating the WebSocket connection.

### 2. `sendHostGeckoPosition`
Replace:
```ts
ws.send(JSON.stringify({ action: 'update_host_gecko_position', data: { position, steps, moments } }));
```
With:
```ts
ws.send(encode({ action: 'update_host_gecko_position', data: { position, steps, moments } }));
```
`encode()` returns a `Uint8Array` which WebSocket sends as a binary frame.

### 3. `sendGuestGeckoPosition`
Same pattern — replace `JSON.stringify(...)` with `encode(...)`:
```ts
ws.send(encode({ action: 'update_guest_gecko_position', data: { position, steps } }));
```

### 4. `sendGeckoPosition` (the plain/legacy one)
Same pattern:
```ts
ws.send(encode({ action: 'update_gecko_position', data: { position } }));
```

### 5. `ws.onmessage` dispatcher
At the top of the existing handler, branch on data type:

```ts
ws.onmessage = (event) => {
  let msg;
  if (event.data instanceof ArrayBuffer) {
    msg = decode(new Uint8Array(event.data));
  } else {
    msg = JSON.parse(event.data);
  }

  // existing switch on msg.action — no changes needed below this point
  const action = msg.action;
  if (action === 'host_gecko_coords') {
    onHostGeckoCoordsRef.current?.(msg.data);
  } else if (action === 'guest_gecko_coords') {
    onGuestGeckoCoordsRef.current?.(msg.data);
  } else if (action === 'gecko_coords') {
    onGeckoCoordsRef.current?.(msg.data);
  }
  // ... rest of existing JSON action handling unchanged
};
```

The key point: once decoded, `msg` has the same shape as before (`{ action: string, data: {...} }`), so the rest of the handler doesn't change.

### 6. Everything else — do NOT change
- `sendRaw` — leave as-is (JSON)
- `getScoreState`, `joinLiveSesh`, `leaveLiveSesh`, `updateGeckoData`, `flush` — leave as JSON sends
- `registerOnScoreState`, `registerOnSync`, `registerOnJoinLiveSesh`, `registerOnLeaveLiveSesh` — unchanged
- Shared values (`peerGeckoPositionSV`, `hostPeerGeckoPositionSV`, `guestPeerGeckoPositionSV`) — the data shape is identical, just the transport changed
- Public return shape of the hook — unchanged

## Backend contract
The Django Channels consumer:
- `receive()` accepts both `text_data` (JSON) and `bytes_data` (msgpack). Both decode to the same dict and route through the same action handler.
- Gecko broadcast handlers (`host_gecko_position_broadcast`, `guest_gecko_position_broadcast`, `gecko_position_broadcast`) send responses as msgpack binary frames.
- All other responses (score_state, join/leave acks, flush acks, energy updates) are still JSON text frames.

## Why this is minimal
- Same message structure — `{ action, data }` is unchanged.
- Same action strings — `update_host_gecko_position`, `host_gecko_coords`, etc.
- Same data fields — `position`, `steps`, `moments`, `from_user`.
- Only the serialization format changes for gecko coord messages.
- The `onmessage` decoder handles both formats transparently.

## Verify
After changes:
1. Open a live session, confirm host frames arrive at guest and vice versa.
2. Confirm position/steps/moments data matches previous JSON version exactly.
3. Confirm non-gecko actions (score state, join/leave, flush) still work (they remain JSON).
4. Check browser devtools Network/WS tab — gecko frames should show as "Binary Frame" while other messages show readable JSON.
