# Droplet Troubleshooting

Quick reference for the backend running on the DO droplet.

## Open a Django shell (connected to live DB)

```bash
cd ~/hellofriendFS/hellofriend/hfroot
source ../venv/bin/activate
python manage.py shell
```

## Check which DB Django is actually using

```bash
python manage.py shell -c "from django.conf import settings; print(settings.DATABASES['default'])"
```

## Inspect / reset a user

Inside `python manage.py shell`:

```python
from users.models import BadRainbowzUser

u = BadRainbowzUser.objects.get(username='some_username')  # or email=...
print(u.is_active, u.is_active_user, u.is_banned_user, u.is_inactive_user, u.login_attempts)
print('usable pw:', u.has_usable_password())

# Reset
u.set_password('tempPass123!')
u.login_attempts = 0
u.is_active = True
u.is_active_user = True
u.is_banned_user = False
u.is_inactive_user = False
u.save()
```

List first few users:

```python
BadRainbowzUser.objects.values_list('id', 'username', 'email')[:10]
```

Test Django auth directly (bypasses SimpleJWT):

```python
from django.contrib.auth import authenticate
print(authenticate(username='some_username', password='tempPass123!'))
```

- Returns user object → Django auth is fine.
- Returns `None` → flags wrong, password wrong, or backend rejecting.

## Gunicorn

### View logs

```bash
sudo journalctl -u gunicorn -n 50 --no-pager
sudo journalctl -u gunicorn -f              # follow live
```

Ignore noise: random `GET /wp-admin/`, `/.env`, `/admin.php` hits are internet bots, harmless 404s.

### View the systemd unit config

```bash
sudo systemctl cat gunicorn
sudo systemctl cat gunicorn | grep -iE "WorkingDirectory|ExecStart|EnvironmentFile"
```

Confirm `WorkingDirectory` points at the checkout you're editing.

### Check gunicorn's live process environment

```bash
sudo systemctl show gunicorn -p MainPID --value
sudo cat /proc/<PID>/environ | tr '\0' '\n' | grep -iE "DB_|SECRET|DJANGO"
```

Use this to confirm gunicorn sees the same `DB_NAME`, `DB_USER`, `DB_HOST`, `DJANGO_SECRET_KEY` as your interactive shell. Systemd does NOT load `~/.bashrc`, so if vars only exist there, gunicorn won't see them.

### Restart / status

```bash
sudo systemctl restart gunicorn
sudo systemctl status gunicorn
```

After any code change, config change, or shell-level env change — **restart gunicorn** or it'll keep serving the old process.

## nginx

### Site is down after a restart but gunicorn is fine

Symptom: you restart, gunicorn comes back, but the whole site is unreachable for hours. The cause is usually that **nginx silently failed its config test and systemd never started it.** Check:

```bash
sudo systemctl status nginx
sudo journalctl -u nginx -n 50 --no-pager
sudo nginx -t
```

Look for:

```
nginx[######]: [emerg] host not found in upstream
   "hf-imagespaces.nyc3.cdn.digitaloceanspaces.com"
   in /etc/nginx/sites-enabled/staging.badrainbowz.com:34
nginx: configuration file /etc/nginx/nginx.conf test failed
```

This means nginx refused to start because it couldn't DNS-resolve the DO Spaces CDN upstream **at config-load time.** The `ExecStartPre=/usr/sbin/nginx -t` failed, so systemd left nginx dead. It is not OOM and not a gunicorn crash — gunicorn stops/starts cleanly on its own.

### Why a static upstream hostname is a landmine

When nginx is given a static hostname in `proxy_pass`/`upstream`, it resolves it **once, at config-load time.** A momentary DNS hiccup at that instant produces `[emerg] host not found in upstream` and nginx won't start **at all** — taking down the entire site, not just CDN proxying. Any future restart/reboot during a DNS blip = total outage. (Later, once DNS resolves, a manual `sudo systemctl restart nginx` "just works" — masking the root cause.)

### Durable fix: resolve the CDN host at request time

Make nginx defer the lookup to a resolver at request time by using a **variable** in `proxy_pass`. First inspect the current block:

```bash
sudo sed -n '20,45p' /etc/nginx/sites-enabled/staging.badrainbowz.com
```

Then rewrite roughly as:

```nginx
# in the http or server block
resolver 127.0.0.53 valid=30s;   # systemd-resolved; or 8.8.8.8 1.1.1.1

location /<spaces-path>/ {
    set $spaces "hf-imagespaces.nyc3.cdn.digitaloceanspaces.com";
    proxy_pass https://$spaces$request_uri;   # variable => runtime DNS
    proxy_set_header Host $spaces;
}
```

The key move is the **variable** in `proxy_pass`. With a variable, nginx defers the DNS lookup to the resolver at request time, so a DNS blip just fails that one CDN request instead of refusing to boot. Catch: a variable `proxy_pass` drops the URI, so append `$request_uri` (or use a `rewrite`) to preserve the path.

### After ANY restart, confirm both services are actually up

A failed nginx start is silent. Get in the habit of:

```bash
systemctl is-active nginx gunicorn
```

Both services are `enabled` so they survive reboot — but "enabled" doesn't mean "started successfully this time."

## Hardening

### Add swap (one time)

A 1GB box with `Swap: 0B` and only ~85Mi truly free is one traffic spike away from a real OOM kill. Check with `free -h`, then:

```bash
sudo fallocate -l 1G /swapfile && sudo chmod 600 /swapfile
sudo mkswap /swapfile && sudo swapon /swapfile
echo '/swapfile none swap sw 0 0' | sudo tee -a /etc/fstab
```

## Recovery recipes

### Login returns 401 after changes

1. `sudo journalctl -u gunicorn -n 50` — confirm it's `POST /users/token/ 401`.
2. Shell: reset password (snippet above).
3. Shell: run `authenticate(...)` to confirm Django accepts it.
4. If shell auth works but app still 401s → `sudo systemctl restart gunicorn`.
5. If still broken → compare shell `DATABASES['default']` to gunicorn's `/proc/<PID>/environ` — they must match.

### Settings file looks wrong / accidentally pushed local

```bash
cd ~/hellofriendFS
git status
git log --oneline -5 -- hellofriend/hfroot/hfroot/settings.py
git checkout <good-commit> -- hellofriend/hfroot/hfroot/settings.py
sudo systemctl restart gunicorn
```

Restores only `settings.py` — leaves DB and other files untouched.

## Notes

- `db.sqlite3` is tracked in the repo but **not used in prod**. Prod uses managed Postgres. Any `modified: db.sqlite3` in `git status` is a red herring.
- Multiple `DATABASES = {...}` blocks exist in `settings.py`; Python uses the **last** assignment — the Postgres one. Don't reorder without thinking.
- There is no `EnvironmentFile=` in the gunicorn unit. Env vars come from wherever systemd picks them up at service start. If you add new required env vars, make sure they're set somewhere systemd reads (unit file `Environment=` lines or an `EnvironmentFile=`), not just `~/.bashrc`.
