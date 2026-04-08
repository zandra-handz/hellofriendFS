// ============================================================
// Gecko Energy WebSocket — Full Workflow Example
// Zero-rerender pattern: WS data → refs → Reanimated shared values
// ============================================================

// --- TYPES ---

export type GeckoEnergyState = {
  energy: number;
  maxEnergy: number;
  depleting: boolean;
  reviving: boolean;
  serverTimestamp: number;
  ratePerSecond: number;
};

// --- API FETCH (initial load before socket connects) ---

export async function fetchGeckoEnergy(
  geckoId: string,
): Promise<GeckoEnergyState> {
  const res = await fetch(
    `https://yourapi.com/api/gecko/${geckoId}/energy/`,
  );
  if (!res.ok) throw new Error('Failed to fetch energy state');
  return res.json();
}

// --- OFFLINE FALLBACK ---

function computeLocalEnergy(
  baseEnergy: number,
  ratePerSecond: number,
  elapsedMs: number,
  max: number,
): number {
  const delta = ratePerSecond * (elapsedMs / 1000);
  return Math.max(0, Math.min(max, baseEnergy + delta));
}

// --- HOOK (refs only, no state, no rerenders) ---

import { useRef, useEffect, useCallback } from 'react';
import { AppState } from 'react-native';

export function useGeckoEnergySocket(geckoId: string) {
  // --- All refs, no state ---
  const energyRef = useRef(0);
  const maxEnergyRef = useRef(100);
  const rateRef = useRef(0);
  const depletingRef = useRef(false);
  const revivingRef = useRef(false);
  const connectedRef = useRef(false);
  const wsRef = useRef<WebSocket | null>(null);
  const localTimerRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const lastServerTimeRef = useRef(Date.now());

  // Callback ref: components register their own update function
  // (e.g., to write into a Reanimated shared value or direct ref)
  const onUpdateRef = useRef<((energy: number) => void) | null>(null);

  const registerOnUpdate = useCallback((cb: (energy: number) => void) => {
    onUpdateRef.current = cb;
  }, []);

  // Apply a server message to refs
  const applyState = useCallback((data: GeckoEnergyState) => {
    energyRef.current = data.energy;
    maxEnergyRef.current = data.maxEnergy;
    rateRef.current = data.ratePerSecond;
    depletingRef.current = data.depleting;
    revivingRef.current = data.reviving;
    lastServerTimeRef.current = data.serverTimestamp;

    // Push to animation layer — no rerender
    onUpdateRef.current?.(data.energy);
  }, []);

  // --- Offline fallback ---
  const stopLocalTick = useCallback(() => {
    if (localTimerRef.current) {
      clearInterval(localTimerRef.current);
      localTimerRef.current = null;
    }
  }, []);

  const startLocalTick = useCallback(() => {
    stopLocalTick();
    const baseEnergy = energyRef.current;
    const baseTime = Date.now();

    localTimerRef.current = setInterval(() => {
      const elapsed = Date.now() - baseTime;
      const estimated = computeLocalEnergy(
        baseEnergy,
        rateRef.current,
        elapsed,
        maxEnergyRef.current,
      );
      energyRef.current = estimated;
      onUpdateRef.current?.(estimated);
    }, 100); // tick every 100ms for smooth animation
  }, []);

  // --- WebSocket connection ---
  const connect = useCallback(() => {
    const ws = new WebSocket(
      `wss://yourapi.com/ws/gecko-energy/${geckoId}/`,
    );

    ws.onopen = () => {
      connectedRef.current = true;
      stopLocalTick(); // server is source of truth now
    };

    ws.onmessage = (event) => {
      const data: GeckoEnergyState = JSON.parse(event.data);
      applyState(data);
    };

    ws.onclose = () => {
      connectedRef.current = false;
      startLocalTick(); // offline fallback kicks in
      // Reconnect after delay
      setTimeout(connect, 3000);
    };

    ws.onerror = () => ws.close();

    wsRef.current = ws;
  }, [geckoId]);

  // --- Lifecycle ---
  useEffect(() => {
    // Fetch initial state, then open socket
    fetchGeckoEnergy(geckoId).then((data) => {
      applyState(data);
      connect();
    });

    // Handle app backgrounding
    const sub = AppState.addEventListener('change', (state) => {
      if (state === 'active' && !connectedRef.current) {
        connect();
      }
    });

    return () => {
      wsRef.current?.close();
      stopLocalTick();
      sub.remove();
    };
  }, [geckoId]);

  // Send actions to server (e.g., revive)
  const send = useCallback((action: object) => {
    if (
      connectedRef.current &&
      wsRef.current?.readyState === WebSocket.OPEN
    ) {
      wsRef.current.send(JSON.stringify(action));
    }
  }, []);

  return {
    energyRef, // read current value anytime without rerender
    connectedRef,
    registerOnUpdate, // hook your animation into this
    send, // send actions like { action: 'revive' }
  };
}

// --- EXAMPLE COMPONENT (zero rerenders from energy updates) ---

// import Animated, {
//   useSharedValue,
//   useAnimatedStyle,
//   withSpring,
// } from 'react-native-reanimated';
//
// export function GeckoEnergyOrb({ geckoId }: { geckoId: string }) {
//   const { registerOnUpdate, send } = useGeckoEnergySocket(geckoId);
//
//   // Reanimated shared value — lives on UI thread, no rerender
//   const energySV = useSharedValue(0);
//
//   useEffect(() => {
//     // Bridge: socket ref updates -> shared value on UI thread
//     registerOnUpdate((energy) => {
//       energySV.value = withSpring(energy, { damping: 20, stiffness: 90 });
//     });
//   }, []);
//
//   const animatedStyle = useAnimatedStyle(() => ({
//     opacity: energySV.value / 100,
//     transform: [{ scale: 0.5 + (energySV.value / 100) * 0.5 }],
//   }));
//
//   return (
//     <Animated.View
//       style={[
//         { width: 100, height: 100, borderRadius: 50, backgroundColor: 'lime' },
//         animatedStyle,
//       ]}
//     />
//   );
// }
