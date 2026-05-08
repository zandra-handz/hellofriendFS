# Gecko Rust Websocket Load Tester

Run on your laptop, not the droplet.

## 1. Provision test data (Django, on the droplet OR locally if your DB is shared)

    python manage.py loadtest_provision --n 50

Writes `loadtest/loadtest_users.json`. Copy it to your laptop if the command
was run on the droplet.

## 2. Install + run

    cd loadtest
    npm install
    node run.mjs --duration 60

Flags: `--url`, `--input`, `--duration`. Defaults target prod.

## 3. Cleanup when done

    python manage.py loadtest_provision --cleanup

## Output

- console: sent / received / drop% / p50 / p95 / p99
- `latencies.csv`: per-message latency in ms

Record the run in `results.md` per the schema there.
