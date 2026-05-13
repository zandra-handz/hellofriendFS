# Staging droplet setup — progress & next steps

## What we built

- **New DigitalOcean droplet** (basic, ~$6/mo, Ubuntu 24.04 LTS, NYC1)
  - Public IP: `146.190.217.221`
  - Hostname on box: `ubuntu-s-1vcpu-1gb-35gb-intel-nyc1`
  - SSH key: `firstSshKey` (same as prod)
- **SSH config alias** added on laptop (`~/.ssh/config`):
  ```
  Host staging
    HostName 146.190.217.221
    User root
    IdentityFile C:\Users\alexa\.ssh\firstSshKey
  ```
  Connect with: `ssh staging`
- **New database in existing managed DO cluster** (not a new cluster — shares resources with prod)
  - DB name: `hf_staging`
  - DB user: dedicated staging user (separate from prod user)
  - Host/port: same as prod (`hf-postgresql-do-user-15838008-0.g.db.ondigitalocean.com`)

## Done on the staging droplet

1. `apt update && apt upgrade -y`
2. Installed system packages: `python3 python3-pip python3-venv python3-dev build-essential git nginx libpq-dev curl pkg-config libssl-dev`
   - Kept local `sshd_config` when prompted (DO modified it to install the SSH key)
3. Installed Rust 1.95.0 via `rustup` (matches prod)
4. Cloned repo: `git clone https://github.com/zandra-handz/hellofriendFS.git` into `/root/hellofriendFS`
5. Created Python venv at `~/hellofriendFS/hellofriend/hfroot/venv` and installed deps
6. Found `requirements.txt` is **out of date** — used `pip freeze` from prod (saved as `/tmp/prod-freeze.txt`) to install the real set
7. Added env vars to `~/.bashrc`:
   ```
   export DJANGO_ENV=staging
   export DB_HOST=hf-postgresql-do-user-15838008-0.g.db.ondigitalocean.com
   export DB_PORT=25060
   export DB_NAME=hf_staging
   export DB_USER=<staging_user>
   export DB_PWD=<staging_password>
   ```
8. `python manage.py check` passes (only 2 harmless ManyToMany W340 warnings, same as prod)

## Where we stopped

`manage.py check` works. Have not yet:
- Confirmed DB connection by running `showmigrations`
- Run `migrate` to create tables in `hf_staging`
- Built the Rust socket
- Set up systemd / nginx / TLS

## Next steps (in order)

### 1. Verify DB connection and apply migrations
```
cd ~/hellofriendFS/hellofriend/hfroot
source venv/bin/activate
python manage.py showmigrations    # should list all migrations as unapplied [ ]
python manage.py migrate           # creates all tables in hf_staging
python manage.py createsuperuser   # for /admin access
```

### 2. Fix `requirements.txt` (cleanup, do later)
The committed `requirements.txt` is missing channels, gunicorn, redis, uvicorn, websockets, etc. On laptop:
- Take `/tmp/prod-freeze.txt` contents → update `requirements.txt` → commit.

### 3. Build the Rust socket
```
cd ~/hellofriendFS/gecko-socket-rust
cargo build --release
```
Will take a while on a 1GB droplet — may need swap if it OOMs. If so:
```
fallocate -l 2G /swapfile && chmod 600 /swapfile && mkswap /swapfile && swapon /swapfile
```

### 4. Decide staging domain
Options:
- (a) Bind to raw IP — simplest, no DNS, but no TLS
- (b) `staging.badrainbowz.com` — needs a DNS A record at the registrar pointing to `146.190.217.221`, then certbot for TLS

`settings.py` is currently set to expect `staging.badrainbowz.com` in `ALLOWED_HOSTS`. If you go with (a), update that to include the IP.

### 5. systemd service files
Copy from prod (`/etc/systemd/system/gunicorn.service` and the Rust socket unit, whatever it's called) to staging. Adjust:
- `Environment=DJANGO_ENV=staging` (not prod)
- `Environment=DB_NAME=hf_staging` and the staging user/password
- Paths should be identical (same `/root/hellofriendFS/...`)

To copy from prod to laptop to staging:
```
# on prod
cat /etc/systemd/system/gunicorn.service
# (paste contents on staging into the same path via nano)
```

Then:
```
systemctl daemon-reload
systemctl enable gunicorn
systemctl start gunicorn
systemctl status gunicorn
```

### 6. nginx config
Copy prod's site config from `/etc/nginx/sites-available/` to staging, adjust `server_name` to the staging hostname (or `_` for IP-only).

```
ln -s /etc/nginx/sites-available/<file> /etc/nginx/sites-enabled/
nginx -t
systemctl reload nginx
```

### 7. TLS (only if using a staging subdomain)
```
apt install -y certbot python3-certbot-nginx
certbot --nginx -d staging.badrainbowz.com
```

### 8. Smoke test
- Hit `https://staging.badrainbowz.com/admin/` (or `http://146.190.217.221/admin/`)
- Test the Rust socket endpoint
- Point a dev build of the React Native app at the staging URL

## Things to remember

- Staging DB lives in the **same managed cluster as prod** — heavy load on staging WILL affect prod. Don't run load tests against it.
- `requirements.txt` is currently misleading (incomplete). Real source of truth is `/tmp/prod-freeze.txt` until cleanup PR lands.
- Prod runs Ubuntu 24.10 (EOL); staging runs 24.04 LTS. Worth migrating prod eventually.
- All Django model edits & migrations are user-handled — don't let Claude touch them.
