# Gecko Rust Websocket Load Test — Runbook

## Quick reference (copy-paste blocks)

Three windows: **Droplet SSH #1** (provision), **Droplet SSH #2** (watch), **Laptop PowerShell** (run). Open all three before starting any tier.

### One-time setup per SSH session

Droplet SSH #1 — every new shell:
```bash
cd ~/hellofriendFS/hellofriend/hfroot
source ../venv/bin/activate
export $(systemctl cat gunicorn | grep -E '^Environment=GECKO_WS_JWT_SECRET' | sed 's/^Environment=//')
```

Laptop PowerShell — every new session:
```powershell
cd C:\Users\alexa\OneDrive\Desktop\CodingSpace\hellofriendFS\loadtest
```

### Per-tier blocks

Replace `<N>` with the tier number. Run the three blocks in order: provision, watcher, test. The watcher block must be running *before* you launch the test.

#### Tier: N=1 (sanity, 10s)

```bash
# Droplet SSH #1
python manage.py loadtest_provision --n 1 --output /tmp/loadtest_users.json
```
```bash
# Droplet SSH #2
pidstat -p $(pgrep -f gecko-socket-rust) 1 25
```
```powershell
# Laptop PowerShell
scp root@HfDroplet:/tmp/loadtest_users.json loadtest_users.json
node run.mjs --duration 10
```

#### Tier: N=5 (60s)

```bash
# Droplet SSH #1
python manage.py loadtest_provision --n 5 --output /tmp/loadtest_users.json
```
```bash
# Droplet SSH #2
pidstat -p $(pgrep -f gecko-socket-rust) 1 75
```
```powershell
# Laptop PowerShell
scp root@HfDroplet:/tmp/loadtest_users.json loadtest_users.json
node run.mjs --duration 60
```

#### Tier: N=50 (60s)

```bash
# Droplet SSH #1
python manage.py loadtest_provision --n 50 --output /tmp/loadtest_users.json
```
```bash
# Droplet SSH #2
pidstat -p $(pgrep -f gecko-socket-rust) 1 75
```
```powershell
# Laptop PowerShell
scp root@HfDroplet:/tmp/loadtest_users.json loadtest_users.json
node run.mjs --duration 60
```

#### Tier: N=100 (60s)

```bash
# Droplet SSH #1
python manage.py loadtest_provision --n 100 --output /tmp/loadtest_users.json
```
```bash
# Droplet SSH #2
pidstat -p $(pgrep -f gecko-socket-rust) 1 75
```
```powershell
# Laptop PowerShell
scp root@HfDroplet:/tmp/loadtest_users.json loadtest_users.json
node run.mjs --duration 60
```

#### Tier: N=250 (60s)

```bash
# Droplet SSH #1
python manage.py loadtest_provision --n 250 --output /tmp/loadtest_users.json
```
```bash
# Droplet SSH #2
pidstat -p $(pgrep -f gecko-socket-rust) 1 75
```
```powershell
# Laptop PowerShell
scp root@HfDroplet:/tmp/loadtest_users.json loadtest_users.json
node run.mjs --duration 60
```

#### Tier: N=500 (60s)

```bash
# Droplet SSH #1
python manage.py loadtest_provision --n 500 --output /tmp/loadtest_users.json
```
```bash
# Droplet SSH #2
pidstat -p $(pgrep -f gecko-socket-rust) 1 75
```
```powershell
# Laptop PowerShell
scp root@HfDroplet:/tmp/loadtest_users.json loadtest_users.json
node run.mjs --duration 60
```

#### Tier: N=1000 (60s)

```bash
# Droplet SSH #1
python manage.py loadtest_provision --n 1000 --output /tmp/loadtest_users.json
```
```bash
# Droplet SSH #2
pidstat -p $(pgrep -f gecko-socket-rust) 1 75
```
```powershell
# Laptop PowerShell
scp root@HfDroplet:/tmp/loadtest_users.json loadtest_users.json
node run.mjs --duration 60
```

### End of session — cleanup

```bash
# Droplet SSH #1
python manage.py loadtest_provision --cleanup
```

---

## What this test does

Drives N parallel two-user "gecko" sessions against the Rust websocket server
running on the droplet, simulating real prod traffic.

Each session:
- Opens 2 websocket connections to `wss://badrainbowz.com/ws/gecko-rust-test/`
  (a "host" and a "guest", paired via a `UserFriendCurrentLiveSesh` row in
  Django).
- Both sides send position updates at 20Hz (`update_host_gecko_position` /
  `update_guest_gecko_position`).
- Each inbound packet broadcasts to exactly one peer in the same shared room.
- For 60 seconds (configurable).

Latency is measured one-way: each outgoing payload bakes `Date.now()` into
`timestamp`; on receipt, the partner computes `arrivalTime - timestamp`.

The test answers: **how many concurrent sessions can the Rust server sustain
at 20Hz without latency degradation or message drops?**

This was originally motivated by Django Channels capping out at a handful of
simultaneous sessions. The Rust rewrite should handle orders of magnitude more.

## Architecture during a run

```
your laptop                            droplet
-----------                            -------
loadtest/run.mjs  ───wss───▶  Nginx ──▶  Rust gecko socket (port 4000)
                                              │
                                              └──HTTP──▶  Django (gunicorn)
                                                              │
                                                              └──▶  Postgres
```

The load tester runs on your laptop, **not** the droplet. Co-locating the
generator with the system under test would skew the numbers by sharing CPU.

---

## How to run it (future runs from your laptop)

### Prerequisites (one-time)

- Node 18+ on the laptop.
- `cd loadtest && npm install` (only needed once, or after package.json changes).
- SSH access to the droplet as `root@HfDroplet` (or whatever target you use).
- The Django management command `loadtest_provision` is already deployed
  (committed in the repo; the droplet pulls it on `git pull`).

### Standard run sequence

1. **Provision test users on the droplet.**

   ```bash
   ssh root@HfDroplet
   cd ~/hellofriendFS/hellofriend/hfroot
   source ../venv/bin/activate

   # Load GECKO_WS_JWT_SECRET into the shell from the gunicorn unit:
   export $(systemctl cat gunicorn | grep -E '^Environment=GECKO_WS_JWT_SECRET' | sed 's/^Environment=//')

   # Provision N session pairs (=> 2N users):
   python manage.py loadtest_provision --n 50 --output /tmp/loadtest_users.json
   ```

2. **Copy the JWT bundle back to your laptop.**

   ```powershell
   scp root@HfDroplet:/tmp/loadtest_users.json loadtest\loadtest_users.json
   ```

3. **Run the load tester.**

   ```powershell
   cd loadtest
   node run.mjs --duration 60
   ```

   Flags:
   - `--duration <seconds>`: how long to drive 20Hz traffic (default 60).
   - `--url <wss-url>`: override target (defaults to prod).
   - `--input <path>`: override JWT bundle location (defaults to
     `./loadtest_users.json`).

4. **Record the result in `results.md`.** Fill in the table row with the
   console output: N, p50/p95/p99, drops%, plus CPU/RSS from the droplet
   (see "Watching the server" below).

5. **Cleanup on the droplet** when you're done:

   ```bash
   python manage.py loadtest_provision --cleanup
   ```

   This deletes every user whose username starts with `loadtest_` and
   cascades through to all their related rows.

### Watching the server during a run

In a separate SSH session to the droplet, run this **before** starting the
load test (or in parallel with it):

```bash
top -p $(pgrep -f gecko-socket-rust) -b -n 90 -d 1 | grep gecko-socket
```

Prints one line per second for 90 seconds — enough to capture a 60s run plus
a buffer. Peak CPU% and RES (resident memory) appear in the columns.

For RSS over a longer window:

```bash
while true; do ps -o rss= -p $(pgrep -f gecko-socket-rust); sleep 5; done
```

### Sanity check before a "real" run

Always start with N=1 for 10s to confirm wiring still works:

```bash
# droplet
python manage.py loadtest_provision --n 1 --output /tmp/loadtest_users.json
```

```powershell
# laptop
scp root@HfDroplet:/tmp/loadtest_users.json loadtest\loadtest_users.json
node run.mjs --duration 10
```

Expect: ~320 sent / ~320 received, **0 drops**, p95 around 30ms (numbers
depend on your distance to the droplet).

---

## Scale-up sequence

Once the N=1 sanity check passes, ramp up to find the breakpoint — the
N at which pass criteria start to fail. That number is the current
capacity ceiling.

### The ramp

Run each step for 60 seconds. Stop when something breaks (drops appear,
p95 climbs over 50ms, or Rust CPU sustains > 70%).

| Step | N (pairs) | Sockets | Inbound msgs/sec | Notes |
|------|-----------|---------|------------------|-------|
| 1 | 1 | 2 | ~40 | Sanity baseline |
| 2 | 5 | 10 | ~200 | Quick smoke |
| 3 | 50 | 100 | ~2,000 | First "real" load |
| 4 | 100 | 200 | ~4,000 | |
| 5 | 250 | 500 | ~10,000 | |
| 6 | 500 | 1,000 | ~20,000 | Past Django Channels' previous ceiling |
| 7 | 1,000 | 2,000 | ~40,000 | Aspirational — only if 500 is healthy |

(Inbound count assumes ~80% of theoretical 20Hz × 2 sockets × N due to
Node `setInterval` drift on Windows.)

### Per-step procedure

For each step, the cycle is:

1. **Re-provision on the droplet** with the new N. JWTs from a previous
   smaller run are still valid (1h TTL), but the new pairs need fresh
   sesh rows.

   ```bash
   # in the SSH session where you already exported GECKO_WS_JWT_SECRET
   python manage.py loadtest_provision --n 50 --output /tmp/loadtest_users.json
   ```

   Provisioning is idempotent — `update_or_create` on the sesh, plus
   `bulk_create(ignore_conflicts=True)` on the users — so re-running with
   a larger N just adds the missing pairs and refreshes existing ones.

2. **scp the bundle back to your laptop.**

   ```powershell
   scp root@HfDroplet:/tmp/loadtest_users.json loadtest\loadtest_users.json
   ```

3. **Start `top` watching the Rust process** in a second SSH session,
   *before* you start the load tester:

   ```bash
   top -p $(pgrep -f gecko-socket-rust) -b -n 90 -d 1 | grep gecko-socket
   ```

4. **Run the load tester.**

   ```powershell
   node run.mjs --duration 60
   ```

5. **Record the row** in `results.md`: date, N, duration, build SHA,
   p50/p95/p99, drops%, peak CPU%, peak RSS MB, plus a short note (e.g.,
   "first run after PERF_TODO #4", or "drops appeared mid-run").

6. **If a step fails the criteria, stop.** Don't blindly try the next
   higher N — diagnose first. The breakpoint *is* the result; the
   debugging is the next task.

### What "fails the criteria" means in practice

The hard fails:

- **Any drops at all.** Even one dropped message is a fail at this
  scale; we want to know exactly when the channel starts saturating.
- **p95 ≥ 50ms** (above the rough internet RTT to the droplet). p95
  rising linearly with N is fine until it crosses the threshold.
- **Rust CPU sustained ≥ 70%** of one core. Brief spikes are OK; a
  steady-state pin is the warning.

The soft fails (worth recording but don't necessarily mean stop):

- p99 climbing while p95 is still healthy — early sign of tail latency
  trouble.
- RSS growing during steady state — could be a leak, but at low N it
  might just be allocator behavior. Re-run to confirm before declaring
  it a fail.
- Connect time growing super-linearly with N — points at the connect
  path (Django hydration, Nginx, TLS) rather than the steady-state
  hot path.

### Between perf changes

The whole point of the scale-up is to push the breakpoint higher each
time we change something in the Rust code. The recommended cadence:

1. Establish a baseline at the current main commit. Find the breakpoint N.
   Record it in `results.md`.
2. Make one perf change (one item from `PERF_TODO.md`). Deploy it to
   the droplet.
3. Re-run the same scale-up. Compare against the baseline row.
4. If the breakpoint moved out: the change worked. Strike the item from
   `PERF_TODO.md`.
5. If the breakpoint didn't move: the change didn't help (or helped
   somewhere we're not measuring). Revert or keep, then move to the
   next item.

One change per scale-up, otherwise you can't attribute what helped.

### When you're done with the session

Always cleanup on the droplet:

```bash
python manage.py loadtest_provision --cleanup
```

Leaving `loadtest_*` users behind pollutes admin views and any
unfiltered queries — and they consume DB rows you don't want hanging
around.

---

## How the setup got built (history — for posterity)

These steps were one-time work and should not need to be repeated unless
the load-test code itself is replaced. Documented here so a future
maintainer can understand the wiring.

### On the laptop / in this repo

1. **Created the Django management command** `loadtest_provision.py` in
   `hellofriend/hfroot/users/management/commands/`. Provisions/cleans up
   test users (username prefix `loadtest_`, `is_test_user=True`) and the
   paired `UserFriendCurrentLiveSesh` rows. Mints JWTs using the same
   secret the websocket validates against.

2. **Created `loadtest/`** with:
   - `package.json` — single dep, `ws`.
   - `run.mjs` — the load driver itself.
   - `README.md` — quick-reference.
   - `results.md` — table for run-to-run records.
   - This file.

3. **Added to `.gitignore`** (only generated files, not the tooling):

   ```
   loadtest/node_modules/
   loadtest/loadtest_users.json   # contains live JWTs
   loadtest/latencies.csv         # per-run output
   ```

### On the droplet

1. **`git pull`** to bring the management command and loadtest tooling
   into the repo.

2. **Verified `pyjwt` was installed** in the Django venv. (Already was,
   because the existing `gecko_socket_token` view uses it.)

3. **Hit a `GECKO_WS_JWT_SECRET` issue** — the secret is set in the
   gunicorn systemd unit (`Environment=GECKO_WS_JWT_SECRET=...`) but not
   in interactive shells. Solution baked into the runbook:
   `export $(systemctl cat gunicorn | grep ... | sed ...)`.

4. **Hit a model save issue** — `BadRainbowzUser.save()` auto-creates a
   `UserFriendCurrentLiveSesh` row with no `other_user`, which then
   crashes in *its* `save()` because that one tries to build a
   `UserFriendLiveSeshLog` requiring host+guest.

   **Fix:** removed line 175 of `users/models.py`
   (`UserFriendCurrentLiveSesh.objects.create(user=self)`). Verified safe
   by greping every call site; all use `.filter().first()`,
   `.update_or_create()`, or wrap `.get()` in try/except. The auto-create
   was redundant — sesh rows get created on demand wherever they're
   needed.

5. **The provision command itself uses `bulk_create`** to bypass the
   `BadRainbowzUser.save()` override entirely. That skips the auxiliary
   rows (`UserProfile`, `GeckoScoreState`, etc.) the load test doesn't
   need — keeps the test footprint smaller and provisioning faster at
   high N. The `rust_live_sesh_context` view tolerates missing
   `score_state` (returns `None`).

6. **Hit a 50% drop on first run** — Rust's host coord handler
   (`main.rs:836`) early-returns if `friend_id.is_none()`. Test sesh rows
   have no `Friend` linked, so host broadcasts were silently dropped;
   guest broadcasts went through (guest path doesn't check `friend_id`).

   **Fix:** load tester sends `set_friend` with a sentinel `friend_id:
   999999` after the host socket connects. The id is only used as
   metadata in the broadcast payload — nothing looks it up server-side.
   Lives in `runPair` in `run.mjs`.

---

## Ideal results

Pass criteria for a single run (per `PERF_TODO.md` and validated at N=1):

| Metric | Target | Why |
|---|---|---|
| **p95 latency** | < 50ms | What real users feel as "instant" for coord updates |
| **p99 latency** | < 100ms | Tail latency — the worst few % users still get acceptable response |
| **Drops** | 0 | Zero tolerance — 20Hz is dense enough that any drop is visible UX |
| **Rust CPU** | < 70% of one core | Headroom for spikes; >70% sustained means we're near tipping point |
| **Rust RSS** | flat during steady state | Linear ramp during connect is fine; growth during sending = leak |
| **Sent vs theoretical** | ~80% of N×40×duration | `setInterval` drift on Windows; not a server problem |

Reference baseline (one run, 2026-05-07):
- N=1, duration=10s, target=prod
- 318 sent, 318 received, 0 drops
- p50 23ms / p95 29ms / p99 48ms
- (CPU/RSS not captured at N=1; trivial)

The bottleneck question is: **at what N do these criteria start to fail?**
That's our current capacity number. Re-run after each perf change to
push the breakpoint higher.

---

## When to be concerned

### Drops > 0

This is the loudest signal something's wrong. Possible causes, in order
of likelihood:

1. **Per-client send channel saturated.** The bounded channel (`mpsc::channel(256)`)
   refuses sends with `try_send` when full — that's by design (see
   PERF_TODO #1). At low N this should never happen; if it does, either a
   client is stuck (won't drain its queue) or we're broadcasting faster
   than the network can ship.
2. **A handler is silently early-returning.** Look for changes to the
   `if !is_host || friend_id.is_none()` style guards in `main.rs`. We
   already hit this once — see history above.
3. **Connection death.** A websocket dropped mid-test. Check the Rust
   logs for `websocket error client_id=...`.

### p95 > 50ms or p99 > 100ms

1. **Server CPU saturated.** Check `top` during the run. If Rust is
   pegged at ~100% of one core, we've hit the single-process limit.
   That's when the multi-node fanout from PERF_TODO #8 becomes
   relevant — but we should be far from that for now.
2. **Lock contention.** The `RwLock<HashMap<...>>` for clients/rooms
   serializes writers. If `mark_seen` (or any other write-locking
   operation) gets re-introduced into the hot path, this is where
   you'll see the symptom.
3. **Network latency to the droplet.** The test runs over the public
   internet. If your home connection is bad that day, latency goes up
   even with a perfectly healthy server. Cross-check by running
   `ping badrainbowz.com` and seeing whether the RTT roughly matches
   the test's p50.

### Rust CPU >70%

1. We're approaching the single-core limit. Capacity is finite — record
   the N at which this happens and that's the current ceiling.
2. **Time to revisit perf TODO** — the next round of optimizations
   should push this number further out.

### RSS growing during steady state

This is a memory leak. Connections during ramp-up should grow RSS
linearly; once all sockets are open and only sending, RSS should be
flat. If it climbs, something is leaking — likely either:

1. Outbound queue not draining (back-pressure not actually firing).
2. Room HashSet refcount bug — `Arc<HashSet>` clones leaking somewhere.
3. Bytes/Vec allocations not being freed in the broadcast loop.

### Sent count way under the expected N×40×duration

Expected count ≈ `N pairs × 2 sockets × duration_sec × 20Hz`. We see
~80% of that on Windows due to `setInterval` drift, which is a Node/OS
issue, not a server issue. If you see *significantly* less than 80%
(say, 50%), then the load tester itself is starved (laptop CPU, network,
or the JS event loop is blocked somewhere).

### Connect time creeping up

`[loadtest] all N pairs online in NNNms` — at low N this should be
under a second. If it grows badly with N (e.g., 30s at N=500), that's
the connect path getting slow, not the steady-state path. Likely
suspects: Django's `live-sesh-context` endpoint (called once per
connect during hydration), Nginx connection limits, or droplet
TLS-handshake throughput.

---

## When NOT to run this test

- **Once we have real users.** Synthetic 20Hz × N traffic against prod
  competes with real user traffic. After we have users, run it only at
  off-peak hours (3 AM), or stand up a separate test instance on a
  different port.
- **Without cleanup planned.** Always pair a provisioning run with a
  matching cleanup. Leftover `loadtest_*` users pollute admin views
  and any unfiltered queries.
- **Without recording the result.** A run not added to `results.md` is
  noise — there's no point doing the test if we can't compare it
  against past or future runs.

---

## Files in this directory

| File | Purpose | In git? |
|---|---|---|
| `RUNBOOK.md` | This file. Permanent reference. | ✅ |
| `README.md` | Quick-start, abbreviated runbook. | ✅ |
| `run.mjs` | The Node load driver. | ✅ |
| `package.json` | npm dependencies (`ws`). | ✅ |
| `results.md` | Table of run-by-run results. | ✅ |
| `loadtest_users.json` | JWT bundle, regenerated each run. | ❌ (gitignored — contains live JWTs) |
| `latencies.csv` | Per-message latency from the last run. | ❌ (gitignored) |
| `node_modules/` | npm install output. | ❌ (gitignored) |
