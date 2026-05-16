# Gunicorn & Droplet Command Reference

Consolidated from: `STAGING_SETUP.md`, `nginx_performance_debugging.txt`,
`redis_performance_debugging.txt`, `MAINTENANCE_CHECKLIST.md`,
`loadtest/RUNBOOK.md`, `loadtest/SESSION_HANDOFF.md`,
`gecko-socket-rust/WATCHING_THE_SOCKET.md`,
`hellofriend/hfroot/DROPLET_TROUBLESHOOTING.md`,
`hellofriend/hfroot/websocket_setup_changelog.txt`.

All droplet commands run as root (or with `sudo`) over SSH. Deploy is a
single DigitalOcean droplet: Django under gunicorn behind nginx, Rust
socket co-located.

---

## ⚠️ Where the actual gunicorn launch command lives

There is **no gunicorn CLI flag set checked into this repo**. The real
`gunicorn ...` command (workers, bind socket, worker class) is the
`ExecStart=` line inside the systemd unit **on the droplet**:

```bash
# View the full gunicorn unit, including the ExecStart command line:
sudo systemctl cat gunicorn

# Just the launch-relevant lines:
sudo systemctl cat gunicorn | grep -iE "WorkingDirectory|ExecStart|EnvironmentFile"

# Edit it (creates/edits a drop-in override):
sudo systemctl edit gunicorn

# After editing the unit:
sudo systemctl daemon-reload
sudo systemctl restart gunicorn
sudo systemctl status gunicorn
```

Known facts about the unit (from `DROPLET_TROUBLESHOOTING.md` &
`websocket_setup_changelog.txt`):

- `ExecStart` was updated to run **uvicorn workers** against
  `hfroot.asgi:application` (ASGI, for WebSocket support).
- It binds a unix socket: nginx proxies to `http://unix:/run/gunicorn.sock`.
- There is **no `EnvironmentFile=`** in the unit. Env vars come from
  `Environment=` lines in the unit itself. Systemd does NOT read
  `~/.bashrc`, so any new required env var must be added to the unit
  (or an `EnvironmentFile=`) — not just the shell.
- The JWT secret is stored as `Environment=GECKO_WS_JWT_SECRET=…` in
  this unit.

---

## SSH / file transfer

```bash
ssh root@HfDroplet                 # prod droplet
ssh staging                        # staging (alias in laptop ~/.ssh/config)

# Pull a file back to the laptop:
scp root@HfDroplet:/tmp/loadtest_users.json loadtest\loadtest_users.json
```

Load the JWT secret into the current SSH shell from the gunicorn unit:

```bash
export $(systemctl cat gunicorn | grep -E '^Environment=GECKO_WS_JWT_SECRET' | sed 's/^Environment=//')
```

---

## Gunicorn (Django) — service control

```bash
sudo systemctl restart gunicorn      # after ANY code/config/env change
sudo systemctl start gunicorn
sudo systemctl enable gunicorn       # start on boot
sudo systemctl status gunicorn
```

Logs:

```bash
sudo journalctl -u gunicorn -n 50 --no-pager   # last 50 lines
sudo journalctl -u gunicorn -f                  # follow live
sudo journalctl -u gunicorn -f | grep gecko_socket_action
sudo journalctl -u gunicorn -f | grep "action=propose_gecko_win"
sudo journalctl -u gunicorn -f | grep "user_id=42"
# slow gecko actions (took= over 50ms):
sudo journalctl -u gunicorn -f | grep gecko_socket_action | awk -F 'took=' '{ if ($2+0 > 50) print }'
sudo journalctl -u gunicorn --since "7 days ago" | grep -iE "error|critical|traceback" | tail -50
```

Inspect the live process environment (confirm gunicorn sees the right
`DB_*` / secrets — they must match your interactive shell):

```bash
sudo systemctl show gunicorn -p MainPID --value
sudo cat /proc/<PID>/environ | tr '\0' '\n' | grep -iE "DB_|SECRET|DJANGO"
```

Reminder: after any code change, config change, or shell-level env
change, **restart gunicorn** or it keeps serving the old process.

---

## Rust gecko socket — service control

Unit name: `gecko-rust.service`.

```bash
sudo systemctl restart gecko-rust.service
systemctl status gecko-rust.service
sudo systemctl edit gecko-rust.service     # edit unit / drop-in

sudo journalctl -u gecko-rust.service -f
sudo journalctl -u gecko-rust.service -n 100
sudo journalctl -u gecko-rust.service -p warning -f
sudo journalctl -u gecko-rust.service --since "10 minutes ago"
sudo journalctl -u gecko-rust.service --since "2026-05-11 22:00:00"
sudo journalctl -u gecko-rust.service -f | grep user_id=42
```

---

## nginx

```bash
ls /etc/nginx/sites-enabled/
sudo cat /etc/nginx/sites-enabled/<site>
sudo cat /etc/nginx/nginx.conf
sudo cat /etc/nginx/nginx.conf | grep -E "worker_processes|worker_connections"
grep -r "proxy_buffering" /etc/nginx/

# Edit, validate, reload (zero-downtime; keeps existing connections):
sudo nano /etc/nginx/sites-enabled/<site>
sudo nano /etc/nginx/nginx.conf
sudo nginx -t                       # ALWAYS validate before reload/restart
sudo systemctl reload nginx
sudo systemctl restart nginx
systemctl status nginx

# Backups (keep OUTSIDE sites-enabled/ — nginx loads every file there):
sudo mkdir -p /root/nginx-backups
sudo cp /etc/nginx/sites-enabled/<site> /root/nginx-backups/<site>.bak-YYYY-MM-DD
sudo cp /etc/nginx/nginx.conf /etc/nginx/nginx.conf.bak-YYYY-MM-DD
# restore:
sudo cp /root/nginx-backups/<site>.bak-YYYY-MM-DD /etc/nginx/sites-enabled/<site>

# Logs:
sudo tail -50 /var/log/nginx/error.log
sudo tail -50 /var/log/nginx/access.log
sudo tail -f  /var/log/nginx/access.log

# Connection counts:
sudo ss -tlnp | grep nginx
sudo ss -tn state established '( sport = :443 or sport = :80 )' | wc -l
```

The Django/WebSocket location block proxies to
`proxy_pass http://unix:/run/gunicorn.sock;`.

---

## redis / disable-THP unit

```bash
systemctl status redis-server
sudo systemctl restart redis-server

# Transparent Huge Pages disable unit (created via nano, runs before redis):
sudo nano /etc/systemd/system/disable-thp.service
cat /etc/systemd/system/disable-thp.service
sudo systemctl daemon-reload
sudo systemctl enable --now disable-thp
systemctl status disable-thp
```

---

## Staging bring-up (systemd / nginx / TLS)

```bash
# Copy prod units to staging, then:
cat /etc/systemd/system/gunicorn.service
systemctl daemon-reload
systemctl enable gunicorn
systemctl start gunicorn
systemctl status gunicorn

# nginx site:
ln -s /etc/nginx/sites-available/<file> /etc/nginx/sites-enabled/
nginx -t
systemctl reload nginx

# TLS:
apt install -y certbot python3-certbot-nginx
certbot --nginx -d staging.badrainbowz.com
```

---

## Routine maintenance

```bash
sudo apt update
sudo apt list --upgradable
sudo apt upgrade                     # review before confirming
sudo certbot certificates            # cert expiry
sudo ufw status verbose              # firewall
```

---

## Restart order when a change touches multiple services

```bash
sudo nginx -t && sudo systemctl restart nginx     # validate first
sudo systemctl restart gunicorn
sudo systemctl restart gecko-rust.service
```
