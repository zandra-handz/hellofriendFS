# HelloFriend — Recurring Maintenance Checklist

A practical maintenance schedule for the Django + Uvicorn + Redis app
running on a DigitalOcean droplet. Assumes a solo-dev workload — cadences
are chosen to catch problems early without becoming a burden.

**Stack assumed:** Django + DRF, Uvicorn (ASGI), Redis, Django Channels
(WebSockets), Celery (if used), PostgreSQL or SQLite, DigitalOcean droplet.
Adjust steps if something doesn't apply.

---

## Recommended Cadence

| Cadence | Time cost | Purpose |
|---|---|---|
| **Weekly** | ~5 min | Catch obvious problems early — is anything broken? |
| **Monthly** | ~30 min | Deeper health check — is anything trending bad? |
| **Quarterly** | ~1–2 hrs | Security, backups, updates. The stuff that's easy to forget. |
| **Annually** | ~half day | Big audits: deps, credentials, disaster recovery test. |

Skipping a cadence once is fine. Skipping for a quarter means you'll be
surprised by something.

---

## Weekly Checklist (~5 min)

Quick eyeball-the-dashboard pass. Run these from the droplet over SSH.

- [ ] **Droplet is reachable and app responds**
  ```bash
  systemctl status redis-server
  systemctl status <your-uvicorn-service>
  systemctl status nginx          # if applicable
  ```
- [ ] **Disk not filling up**
  ```bash
  df -h
  ```
  Flag if any partition is >80% full.
- [ ] **Memory + swap sanity**
  ```bash
  free -h
  ```
  No swap should be in use. If RAM is consistently >90%, plan.
- [ ] **Recent error spike?**
  ```bash
  sudo journalctl -u <your-uvicorn-service> --since "7 days ago" | grep -iE "error|critical|traceback" | tail -50
  ```
- [ ] **Uptime looks reasonable** (unexpected reboots?)
  ```bash
  uptime
  last reboot | head -5
  ```

---

## Monthly Checklist (~30 min)

### Redis
- [ ] **Intrinsic latency spot-check**
  ```bash
  redis-cli --intrinsic-latency 100
  ```
  Expect max under ~1ms on a clean host. Investigate if it regresses.
- [ ] **Internal latency events**
  ```bash
  redis-cli LATENCY LATEST
  redis-cli LATENCY DOCTOR
  ```
- [ ] **Slow commands**
  ```bash
  redis-cli SLOWLOG GET 25
  redis-cli SLOWLOG RESET          # clear after reviewing
  ```
- [ ] **Memory + eviction trends**
  ```bash
  redis-cli INFO memory | grep -E "used_memory_human|fragmentation_ratio|evicted_keys"
  redis-cli INFO stats | grep -E "rejected_connections|total_connections_received"
  ```
- [ ] **THP still disabled** (survives kernel updates?)
  ```bash
  cat /sys/kernel/mm/transparent_hugepage/enabled    # expect [never]
  systemctl status disable-thp
  ```

See `redis_performance_debugging.txt` for deeper Redis diagnostics.

### Django / App
- [ ] **Migrations applied, no pending**
  ```bash
  python manage.py showmigrations | grep "\[ \]"
  ```
- [ ] **No stuck Celery tasks / dead workers** (if using Celery)
  ```bash
  celery -A <project> inspect active
  celery -A <project> inspect reserved
  ```
- [ ] **Django system check**
  ```bash
  python manage.py check --deploy
  ```
- [ ] **Static files current** (if deploys changed them)
  ```bash
  python manage.py collectstatic --dry-run
  ```
- [ ] **Log files rotating** (not one giant 5GB log)
  ```bash
  ls -lah /var/log/ | head -30
  ls -lah ./logs/ 2>/dev/null
  ```

### Host
- [ ] **CPU steal over a real window**
  ```bash
  vmstat 1 60
  ```
  Watch the `st` column. Bursts = noisy neighbor; plan a resize if bad.
- [ ] **Load average reasonable for CPU count**
  ```bash
  uptime
  nproc
  ```
- [ ] **WebSocket / Channels health** (if applicable)
  Run the checks in `socket_lag_investigation.md`.

---

## Quarterly Checklist (~1–2 hrs)

### Backups (the one you'll regret skipping)
- [ ] **Database backup runs and is restorable**
  - Confirm a recent backup exists.
  - **Actually restore it into a scratch DB** and query a row.
    A backup you haven't restored is not a backup.
- [ ] **Droplet snapshot exists**
  - Check DO console for recent snapshot.
  - Take a fresh one if none in the last quarter.
- [ ] **Media / uploaded files backed up** (if applicable)

### Security
- [ ] **OS security updates**
  ```bash
  sudo apt update
  sudo apt list --upgradable
  sudo apt upgrade          # review before confirming
  ```
- [ ] **Python dependency vulnerabilities**
  ```bash
  pip install pip-audit
  pip-audit -r requirements.txt
  ```
  Or use `safety check` if preferred.
- [ ] **Django `check --deploy` clean**
  ```bash
  python manage.py check --deploy
  ```
- [ ] **Review `SECURITY_AUDIT.txt`** — anything overdue?
- [ ] **SSL cert expiry** (if you manage certs directly)
  ```bash
  sudo certbot certificates            # if using certbot
  ```
- [ ] **Firewall / UFW rules still correct**
  ```bash
  sudo ufw status verbose
  ```
- [ ] **SSH: no unused keys in `~/.ssh/authorized_keys`**

### Performance / Capacity
- [ ] **Database size trend** — growing faster than expected?
- [ ] **Redis memory trend** — approaching `maxmemory`?
- [ ] **Review `SLOWLOG` and slow DB queries accumulated over the quarter**
- [ ] **Droplet right-sized?** — if you're consistently >70% RAM or CPU,
      plan a resize before it bites.

---

## Annual Checklist (~half day)

### Dependencies
- [ ] **Major version audit** — any library 2+ major versions behind?
- [ ] **Django LTS status** — still on a supported version?
- [ ] **Python version** — still receiving security updates?
      (Check https://devguide.python.org/versions/)
- [ ] **Node / React / frontend deps** (for `hellofriendreact/`)
  ```bash
  npm outdated
  npm audit
  ```
- [ ] **Remove unused requirements** — cross-reference `unused_requirements.txt`.

### Credentials & Secrets
- [ ] **Rotate Django `SECRET_KEY`** (plan for session/logout impact).
- [ ] **Rotate DB passwords**.
- [ ] **Rotate API keys** (DO token, third-party APIs).
- [ ] **Rotate JWT signing keys** if applicable.
- [ ] **Audit `.env` / secrets files** — anything unused, anything leaked
      to git history?
  ```bash
  git log --all --full-history -- '*.env*'
  ```

### Disaster Recovery Test
- [ ] **Spin up a fresh droplet from snapshot + DB backup.**
      Can you actually bring the app up from scratch? Time yourself.
      Document what was missing from the runbook.
- [ ] **Update the recovery runbook** with whatever tripped you up.

### Documentation Sweep
- [ ] `CLAUDE.md` / `README.md` still accurate?
- [ ] `DROPLET_TROUBLESHOOTING.md` — any new issues worth adding?
- [ ] `ISSUES_TO_FIX.txt` — clear out anything done; re-prioritize.

---

## Log Template

Keep a terse log at the bottom of this file — one line per completed check.
Skip the ceremony, just leave a trail.

```
YYYY-MM-DD  weekly   — all green
YYYY-MM-DD  monthly  — Redis evicted_keys up from 0 to 3200; added maxmemory
YYYY-MM-DD  quarterly — restored DB backup, all OK; apt upgrade done
```

### Log

- 2026-04-19  initial  — Redis THP disabled, latency monitor enabled;
                         see `redis_performance_debugging.txt`.
