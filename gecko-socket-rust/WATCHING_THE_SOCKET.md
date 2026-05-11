# Watching the Rust gecko socket on the droplet

The Rust socket runs as a systemd service (`gecko-rust.service`). All stdout/stderr
goes to journald automatically — no extra setup needed to view logs.

---

## Live tail

```bash
sudo journalctl -u gecko-rust.service -f
```

This is the default "what is the socket doing right now" view. Leave it open in
a terminal while you use the app.

---

## Other useful views

```bash
# Last 100 lines, no follow
sudo journalctl -u gecko-rust.service -n 100

# Warnings and errors only (live)
sudo journalctl -u gecko-rust.service -p warning -f

# Logs since a specific time
sudo journalctl -u gecko-rust.service --since "10 minutes ago"
sudo journalctl -u gecko-rust.service --since "2026-05-11 22:00:00"

# Filter by content (e.g., one user's activity)
sudo journalctl -u gecko-rust.service -f | grep user_id=42

# Current service status (running? memory? CPU? last start time?)
systemctl status gecko-rust.service
```

---

## Crank verbosity temporarily (debug logs)

The socket runs at `info` level by default. To see `debug!`-level messages
(per-action detail, internal state changes) without editing code:

```bash
sudo systemctl edit gecko-rust.service
```

In the editor that opens, add:

```ini
[Service]
Environment="RUST_LOG=gecko_socket_rust=debug"
```

Save and exit, then restart:

```bash
sudo systemctl restart gecko-rust.service
sudo journalctl -u gecko-rust.service -f
```

**Revert when done** (debug logs are noisy and add I/O):

```bash
sudo systemctl edit gecko-rust.service
```

Delete the override lines, save, then:

```bash
sudo systemctl restart gecko-rust.service
```

---

## Restart workflow after a code change

```bash
cd ~/hellofriendFS/gecko-socket-rust
cargo build --release
sudo systemctl restart gecko-rust.service
sudo journalctl -u gecko-rust.service -f
```

If the change also affects Django or nginx config:

```bash
sudo systemctl restart gunicorn
sudo systemctl restart nginx
```

---

## What "healthy" looks like at startup

```
Started gecko-rust.service - Gecko Rust WebSocket Server.
INFO gecko_socket_rust: Rust websocket running at http://127.0.0.1:4000
```

That's the bind-success line. After that, every WS connect/disconnect and
forwarded action will log under that service.

---

## Common warnings (not bugs)

- `WebSocket protocol error: Connection reset without closing handshake` —
  client disconnected ungracefully (app backgrounded, network drop, force-quit).
  Expected on mobile. Only worry if the rate spikes under load.

---
---

# Watching the Django side (gunicorn)

When the Rust socket forwards an action to Django (via `proxy_action_to_django`),
Django handles it in `gecko_socket_action` and returns a response. To see what
Django is doing — and how long each action takes — watch its journal.

---

## Live tail

```bash
sudo journalctl -u gunicorn -f
```

Look for `[gecko_socket_action]` lines — every forwarded action from the Rust
socket logs a timing line here.

---

## Filtering for socket-action traffic only

```bash
# Only the socket-action timing lines
sudo journalctl -u gunicorn -f | grep gecko_socket_action

# One specific action across all users
sudo journalctl -u gunicorn -f | grep "action=propose_gecko_win"

# One user across all actions
sudo journalctl -u gunicorn -f | grep "user_id=42"

# Slow calls only (anything over 50ms — adjust as needed)
sudo journalctl -u gunicorn -f | grep gecko_socket_action | awk -F 'took=' '{ if ($2+0 > 50) print }'
```

---

## What a healthy log line looks like

```
INFO [gecko_socket_action] action=propose_gecko_win user_id=42 took=8.74ms
```

`took=X.XXms` is **pure Django time** — parser, dispatch, business logic, renderer.
It does **not** include the network hop from Rust or any gunicorn worker queue time.

---

## Comparing Rust and Django timings

Run any FE action, then check both journals side-by-side:

```bash
# Terminal 1
sudo journalctl -u gecko-rust.service -f

# Terminal 2
sudo journalctl -u gunicorn -f | grep gecko_socket_action
```

You'll see paired lines for each action:

- **Rust:** `proxy_action_to_django{action=... user_id=...}: close time.busy=Xms time.idle=Yms`
  → total Rust-perspective time (network round-trip + everything Django did).
- **Django:** `[gecko_socket_action] action=... user_id=... took=Zms`
  → pure Django time.

The difference (`Rust time` − `Django time`) is **proxy hop overhead**:
loopback HTTP + gunicorn worker pickup + msgpack encode/decode.

| Symptom | Likely cause |
| --- | --- |
| Rust 12ms, Django 8ms | Healthy. ~4ms proxy overhead on loopback. |
| Rust 80ms, Django 8ms | gunicorn worker contention or request queueing. Check worker count. |
| Rust 200ms, Django 195ms | Django itself is slow. Profile the handler in `gecko_match_helpers` etc. |
| Rust 200ms, Django <1ms or no line | Rust never reached Django — check Django reachability, secret header, URL. |

---

## Restart workflow

After a Django code change:

```bash
sudo systemctl restart gunicorn
sudo journalctl -u gunicorn -f
```

If you also changed nginx config:

```bash
sudo nginx -t                       # validate before restarting
sudo systemctl restart nginx
```

---

## Cranking Django log verbosity

Django uses its own logging config (typically in `settings.py` / `localsettings.py`
under `LOGGING`). To temporarily see more detail without code changes, set the
`DJANGO_LOG_LEVEL` env var in the systemd unit:

```bash
sudo systemctl edit gunicorn
```

Add:

```ini
[Service]
Environment="DJANGO_LOG_LEVEL=DEBUG"
```

This only takes effect if your `LOGGING` config reads `DJANGO_LOG_LEVEL` from the
environment. If it doesn't, edit the logger level in `settings.py` directly and
restart gunicorn.

**Revert when done** — DEBUG-level Django logs are extremely noisy (every ORM
query, every middleware step).

