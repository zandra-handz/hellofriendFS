# Socket Lag Investigation — To Do Tomorrow

## Symptom observed

- Testing with two clients broadcasting to the same channel (host + guest gecko positions).
- Both clients experienced lag; guest position update was worse.
- Characteristic pattern: **clients freeze, then all queued positions arrive in order (none skipped)**.
- Only reproduced on a new/unfamiliar WiFi network.

---

## Most likely cause: TCP head-of-line (HOL) blocking

- WebSockets run over TCP.
- If one packet is lost or delayed, every later packet waits in the kernel buffer until the missing one is retransmitted.
- When the retransmit arrives, the whole backlog flushes at once → "frozen, then burst" behavior.
- This matches the symptom exactly (in-order delivery, no skipped messages).
- New WiFi makes this worse because of:
  - Weak signal / interference causing packet loss
  - Higher RTT amplifying every retransmit wait
  - AP power-save modes batching frames
  - Captive portals / carrier-grade proxies sometimes buffering long-lived WS connections

---

## Diagnostic steps (do these first)

### 1. Confirm it's the network, not the app

- Run a continuous ping to the server while reproducing the bug:
  - Windows: `ping -t <server-hostname>`
  - Mac/Linux: `ping <server-hostname>`
- Watch for:
  - Latency spikes (20ms → 800ms → 20ms) = congestion/interference
  - "Request timed out" lines = packet loss
- If ping freezes at the same moment the sockets freeze → 100% network.

### 2. Measure sustained loss

- `ping -n 100 <server>` (Windows) or `ping -c 100 <server>` (Mac/Linux)
- Check the reported `% packet loss`:
  - \>1% on WiFi is enough to cause visible WS stalls
  - \>5% is bad

### 3. Find where loss happens

- `tracert <server>` (Windows) or `traceroute <server>` / `mtr <server>` (Mac/Linux)
- `mtr` is the best tool — live updating, shows loss % per hop
- Interpretation:
  - Hop 1 = your router / local WiFi
  - Hops 3–5 = your ISP
  - Near end = server/host side

### 4. Isolate WiFi vs everything else

- Plug in ethernet OR tether to phone hotspot, repeat scenario.
- If lag disappears on ethernet → it's the WiFi link itself.

### 5. Inspect in browser DevTools

- DevTools → Network → WS → Messages
- Look at timestamps of incoming frames.
- A 2-second gap followed by 15 messages within 1ms = TCP HOL burst (confirms retransmit theory).

---

## Backend checks

### Redis / Channel Layer config (settings.py:138–150)

Current config:

```python
CHANNEL_LAYERS = {
    'default': {
        'BACKEND': 'channels_redis.core.RedisChannelLayer',
        'CONFIG': {
            'hosts': [(os.getenv('REDIS_HOST', '127.0.0.1'), 6379)],
            'capacity': 50,   # default 100
            'expiry': 10,     # default 60
        },
        'POOL': {'max_connections': 10},
    },
}
```

- **`capacity: 50`** — each channel can only hold 50 unprocessed messages before `channels_redis` raises `ChannelFull` on send.
  - At ~20 Hz send rate, that's only 2.5 seconds of buffer per client.
  - If a client's consumer is slow to drain, `group_send` to the group can start failing for that client.
  - Consider bumping back toward the default (100) or higher if we're broadcasting frequently.
- **`expiry: 10`** — messages older than 10s get evicted from Redis.
  - Comment in the file says "3 seconds" but the value is 10 — fix the misleading comment.
  - 10s is fine for real-time; a 10s-old position is useless anyway.
- **`max_connections: 10`** — low-ish for a broadcast scenario with many concurrent WS clients. If we scale up, revisit.
- **Redis is NOT on `127.0.0.1` in production.** The `127.0.0.1` is just the dev fallback — `REDIS_HOST` env var points elsewhere on the droplet. This means every `group_send` is a network round-trip to Redis.

**Action items:**
- [ ] Raise `capacity` to 100 (default) or 200 and retest.
- [ ] Fix the misleading `expiry` comment ("3 seconds" → "10 seconds").
- [ ] Check Redis latency during a lag event: `redis-cli --latency` on the server.

### Redis is remote — latency implications

Because Redis lives off-box, every WebSocket message does this round trip:

- Client → Django consumer → **network hop to Redis** → Redis fans out → **network hop back** to each consumer → send to client.
- At 20 Hz × 2 clients that's ~40 Redis round-trips per second per direction.
- If Redis is in a different region or behind a slow link, this is a fixed latency floor independent of the client WiFi issue.

**Things to check:**

- [ ] Where is Redis actually hosted? Same droplet on a private interface? Another droplet? DigitalOcean Managed Redis? Same region?
- [ ] Measure the hop — on the app droplet run: `redis-cli -h $REDIS_HOST --latency`
  - Under 1–2ms = fine
  - 2–10ms = noticeable at 20Hz
  - \>10ms = bad, will compound with any WiFi loss
- [ ] Is Redis over TLS (`rediss://`)? Managed Redis usually requires it; adds handshake + per-command overhead.
- [ ] If Redis is on another droplet, confirm we're using the **DigitalOcean private network** IP (not public) — avoids the public internet hop.
- [ ] Bump `max_connections` above 10 — if Redis is remote and slow, 10 pooled connections may bottleneck under concurrent broadcasts.
- [ ] Check the Redis server's own load: `redis-cli info stats` → `instantaneous_ops_per_sec`, `total_connections_received`. Rule out a saturated Redis.

### Nginx (in use as reverse proxy)

Nginx can buffer WebSocket traffic unless explicitly told not to. Verify the server block has:

```nginx
location /ws/ {
    proxy_pass http://your-upstream;
    proxy_http_version 1.1;
    proxy_set_header Upgrade $http_upgrade;
    proxy_set_header Connection "upgrade";
    proxy_set_header Host $host;
    proxy_set_header X-Real-IP $remote_addr;

    # Critical for low-latency WS:
    proxy_buffering off;
    tcp_nodelay on;

    # Keep long-lived connections open:
    proxy_read_timeout 3600s;
    proxy_send_timeout 3600s;
}
```

**Action items:**
- [ ] SSH to the droplet, check `/etc/nginx/sites-enabled/*` for the WS location block.
- [ ] Confirm `proxy_buffering off;` and `tcp_nodelay on;` are set.
- [ ] Confirm `proxy_read_timeout` is long enough (default 60s will kill idle WS).

### Nagle's algorithm / TCP_NODELAY

- Nagle: TCP bundles small sends to reduce overhead; adds latency for real-time.
- TCP_NODELAY disables Nagle. Usually set at the server/proxy layer.
- Less likely to be the cause here (Nagle delays are small and consistent, not long freezes), but worth verifying nginx has `tcp_nodelay on;`.

---

## Payload & frequency review

### Sample payload from logs

Each `update_host_gecko_position` is ~1.5–2 KB and contains:

- `pos` — 2 floats
- `steps` — 4 points
- `step_angles` — 4 floats
- `held_moments` — 8 floats, all currently `-100.5` (placeholder)
- `moments` — 30 slots, only ~3 populated; rest are `[0, 0, 0, 0]` padding

~70% of each message is dead weight.

### Send rate

- From the log: two messages ~60ms apart → ~16–20 Hz per client.
- Aggregate for 2 clients: ~80 KB/s up and down — not bandwidth-limited.
- But every send is another chance for a lost packet to stall the stream.

### Action items

- [ ] Trim payload: drop `[0,0,0,0]` slots and `-100.5` placeholders before sending. Send only populated entries + a count.
- [ ] Throttle client send rate to ~10 Hz; interpolate between frames on the receiver side.
- [ ] Add a sequence number + timestamp to each position message so the client can drop stale ones on burst-arrival (render latest, skip the backlog) instead of replaying every queued position.

---

## Frontend send rate — where to change Hz

- Hz is set **on the client**, not the backend.
- Frontend lives in `hellofriendreact/` (separate repo).
- Search the React code for whatever triggers `update_host_gecko_position`.
- Look for one of:
  - `setInterval(... , 50)` → change to `100` for 10 Hz
  - `requestAnimationFrame` loop sending on every frame → add a timestamp throttle
  - Event-driven `onMove → send` → wrap in throttle/debounce

Simple throttle gate:

```js
let lastSent = 0;
function sendPosition(data) {
  const now = Date.now();
  if (now - lastSent < 100) return; // 100ms = 10 Hz
  lastSent = now;
  socket.send(JSON.stringify(data));
}
```

---

## Priority order for tomorrow

1. **Diagnose the network** (ping + mtr + ethernet comparison) — confirms root cause in 5 min.
2. **Check nginx config** for `proxy_buffering off` and `tcp_nodelay on`.
3. **Revisit Redis channel layer `capacity`** — bump to 100+.
4. **Trim payload padding** — quick, big ratio win.
5. **Throttle client send rate** to 10 Hz + interpolate on receiver.
6. **Add seq number + timestamp** so clients can skip stale positions on burst-arrival.
7. Longer-term: if WS-over-TCP keeps being a problem on bad networks, evaluate WebRTC DataChannel (unreliable mode) for position data — avoids HOL blocking entirely.
