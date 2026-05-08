/**
 * Drives N parallel 2-user sessions against the Rust gecko websocket and
 * measures one-way latency.
 *
 * Reads ./loadtest_users.json (produced by `manage.py loadtest_provision`),
 * connects 2N sockets to wss://badrainbowz.com/ws/gecko-rust-test/, waits for
 * peer_presence:online on both sides of each pair, then drives 20Hz position
 * updates for DURATION_SEC. Latency is computed from a `timestamp` baked into
 * each payload to its arrival time on the other side.
 *
 * Run from your laptop, not the droplet.
 *
 *   node run.mjs                       # defaults: bundled JSON, 60s
 *   node run.mjs --duration 30
 *   node run.mjs --url wss://other.host/ws/gecko-rust-test/
 *   node run.mjs --input ./loadtest_users.json
 */

import { readFileSync, writeFileSync } from "node:fs";
import WebSocket from "ws";

const args = Object.fromEntries(
  process.argv.slice(2).reduce((acc, cur, i, arr) => {
    if (cur.startsWith("--") && i + 1 < arr.length) acc.push([cur.slice(2), arr[i + 1]]);
    return acc;
  }, [])
);

const URL = args.url ?? "wss://badrainbowz.com/ws/gecko-rust-test/";
const INPUT = args.input ?? "./loadtest_users.json";
const DURATION_SEC = Number(args.duration ?? 60);
const HZ = 20;
const SEND_INTERVAL_MS = 1000 / HZ;
const HANDSHAKE_TIMEOUT_MS = 15_000;

const pairs = JSON.parse(readFileSync(INPUT, "utf8"));
console.log(`[loadtest] ${pairs.length} pairs (${pairs.length * 2} sockets), ${DURATION_SEC}s @ ${HZ}Hz`);
console.log(`[loadtest] target: ${URL}`);

let totalSent = 0;
let totalReceived = 0;
const latencies = [];

function openSocket(token, role, pairIndex) {
  return new Promise((resolve, reject) => {
    const ws = new WebSocket(URL, ["gecko.v1", `jwt.${token}`]);
    const state = {
      ws, role, pairIndex,
      peerOnline: false,
      sent: 0,
      received: 0,
    };

    const handshakeTimer = setTimeout(() => {
      reject(new Error(`pair ${pairIndex} ${role}: handshake timeout`));
    }, HANDSHAKE_TIMEOUT_MS);

    ws.on("open", () => {
      ws.send(JSON.stringify({ action: "join_live_sesh" }));
      ws.send(JSON.stringify({ action: "request_peer_presence" }));
    });

    ws.on("message", (buf, isBinary) => {
      let msg;
      if (isBinary) {
        try {
          msg = decodeMsgpackTimestamp(buf);
        } catch {
          return;
        }
      } else {
        try { msg = JSON.parse(buf.toString()); } catch { return; }
      }

      if (msg?.action === "peer_presence" && msg?.data?.online === true) {
        if (!state.peerOnline) {
          state.peerOnline = true;
          clearTimeout(handshakeTimer);
          resolve(state);
        }
      } else if (msg?.action === "host_gecko_coords" || msg?.action === "guest_gecko_coords") {
        const ts = msg?.data?.timestamp;
        if (typeof ts === "number") {
          const lat = Date.now() - ts;
          latencies.push(lat);
          state.received++;
          totalReceived++;
        }
      }
    });

    ws.on("error", (err) => {
      clearTimeout(handshakeTimer);
      reject(err);
    });

    ws.on("close", () => {
      clearTimeout(handshakeTimer);
    });
  });
}

// Minimal msgpack timestamp extractor — finds `timestamp` key + reads following number.
// Avoids pulling in a full msgpack dep; brittle but adequate when the server keeps the
// {action, data:{...timestamp:N...}} shape stable.
function decodeMsgpackTimestamp(buf) {
  const s = buf.toString("binary");
  const idx = s.indexOf("timestamp");
  if (idx < 0) return null;
  const after = idx + "timestamp".length;
  const marker = buf[after];
  if (marker === 0xcb) {
    const ts = buf.readDoubleBE(after + 1);
    return { action: "host_gecko_coords", data: { timestamp: ts } };
  }
  if (marker === 0xcf) {
    const ts = Number(buf.readBigUInt64BE(after + 1));
    return { action: "host_gecko_coords", data: { timestamp: ts } };
  }
  if (marker === 0xd3) {
    const ts = Number(buf.readBigInt64BE(after + 1));
    return { action: "host_gecko_coords", data: { timestamp: ts } };
  }
  return null;
}

async function runPair(pair, pairIndex) {
  const [host, guest] = await Promise.all([
    openSocket(pair.host_token, "host", pairIndex),
    openSocket(pair.guest_token, "guest", pairIndex),
  ]);

  // Host needs friend_id set; otherwise Rust silently drops host coord broadcasts
  // (main.rs:836 early-returns if friend_id.is_none()). Sentinel id used only as
  // metadata in the broadcast payload — never looked up server-side.
  host.ws.send(JSON.stringify({
    action: "set_friend",
    data: { friend_id: 999999 },
  }));

  return { host, guest };
}

function startSending(state) {
  const action = state.role === "host" ? "update_host_gecko_position" : "update_guest_gecko_position";
  const interval = setInterval(() => {
    if (state.ws.readyState !== WebSocket.OPEN) {
      clearInterval(interval);
      return;
    }
    state.ws.send(JSON.stringify({
      action,
      data: {
        position: [Math.random() * 100, Math.random() * 100],
        steps: [],
        steps_len: 0,
        first_fingers: [],
        held_moments: [],
        held_moments_len: 0,
        moments: [],
        moments_len: 0,
        timestamp: Date.now(),
      },
    }));
    state.sent++;
    totalSent++;
  }, SEND_INTERVAL_MS);
  return interval;
}

(async () => {
  const t0 = Date.now();
  console.log("[loadtest] opening sockets…");

  // Stagger pair starts so we don't slam Django with N parallel hydration
  // calls at once. Each runPair still opens host+guest in parallel internally.
  // 100ms between pair starts means ~10 in-flight handshakes at any time.
  const STAGGER_MS = 100;
  const pendingPairs = [];
  for (let i = 0; i < pairs.length; i++) {
    pendingPairs.push(runPair(pairs[i], i));
    if (i < pairs.length - 1) {
      await new Promise((r) => setTimeout(r, STAGGER_MS));
    }
  }
  const sessions = await Promise.all(pendingPairs);
  console.log(`[loadtest] all ${sessions.length} pairs online in ${Date.now() - t0}ms`);

  console.log(`[loadtest] driving ${HZ}Hz for ${DURATION_SEC}s…`);
  const intervals = sessions.flatMap(({ host, guest }) => [startSending(host), startSending(guest)]);

  await new Promise((r) => setTimeout(r, DURATION_SEC * 1000));

  intervals.forEach(clearInterval);
  console.log("[loadtest] done sending. waiting 1s for in-flight…");
  await new Promise((r) => setTimeout(r, 1000));
  sessions.forEach(({ host, guest }) => { host.ws.close(); guest.ws.close(); });

  latencies.sort((a, b) => a - b);
  const p = (q) => latencies[Math.min(latencies.length - 1, Math.floor(latencies.length * q))] ?? 0;
  const expected = totalSent;
  console.log("\n=== RESULTS ===");
  console.log(`sent:       ${totalSent}`);
  console.log(`received:   ${totalReceived}`);
  console.log(`drops:      ${expected - totalReceived} (${((1 - totalReceived / expected) * 100).toFixed(2)}%)`);
  console.log(`p50:        ${p(0.5)} ms`);
  console.log(`p95:        ${p(0.95)} ms`);
  console.log(`p99:        ${p(0.99)} ms`);

  writeFileSync("./latencies.csv", "latency_ms\n" + latencies.join("\n"));
  console.log("[loadtest] wrote latencies.csv");
  process.exit(0);
})().catch((err) => {
  console.error("[loadtest] FATAL:", err);
  process.exit(1);
});
