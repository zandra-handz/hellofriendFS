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
