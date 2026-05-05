// import React, {
//   createContext,
//   useCallback,
//   useContext,
//   useEffect,
//   useMemo,
//   useRef,
//   useState,
// } from "react";
// import { AppState, type AppStateStatus } from "react-native";
// import {
//   useSharedValue,
//   withTiming,
//   type SharedValue,
// } from "react-native-reanimated";
// import * as SecureStore from "expo-secure-store";
// import notepack from "notepack.io";

// import manualGradientColors from "@/app/styles/StaticColors";

// // ---------------------------------------------------------------------------
// // Rust gecko socket migration notes
// // ---------------------------------------------------------------------------
// // This context now points at the Rust gecko socket (`/ws/gecko-rust-test/`)
// // instead of the Django Channels consumer (`/ws/gecko-energy/`). The wire
// // format is the same: JSON for control frames, msgpack (notepack) for the
// // high-frequency gecko_coords/host_gecko_coords/guest_gecko_coords/
// // all_host_capsules/capsule_progress frames.
// //
// // Differences vs the channels socket:
// //   * Auth: Rust takes ?user_id=N as a query param (no token validation).
// //     We extract user_id from the JWT FE-side. For production the Rust
// //     server should be hardened to validate the token; until then DO NOT
// //     expose this socket beyond your trusted network.
// //   * New inbound action `force_disconnect`: Rust sends this when a newer
// //     connection for the same user replaces an older one. We must NOT
// //     reconnect on it, otherwise two devices will fight forever.
// //   * Two new server-pushed actions for the win-match flow:
// //     `gecko_win_match_pending_accept_partner` and `gecko_win_match_finalized`.
// // ---------------------------------------------------------------------------

// const RUST_SOCKET_HOST = "wss://badrainbowz.com";
// const RUST_SOCKET_PATH = "/ws/gecko-rust-test/";

// function decodeJwtUserId(token: string): number | null {
//   try {
//     const payload = token.split(".")[1];
//     if (!payload) return null;
//     const b64 = payload.replace(/-/g, "+").replace(/_/g, "/");
//     const padded = b64 + "=".repeat((4 - (b64.length % 4)) % 4);
//     // atob is polyfilled in modern RN runtimes.
//     const decoded =
//       typeof atob !== "undefined"
//         ? atob(padded)
//         : // eslint-disable-next-line @typescript-eslint/no-var-requires
//           Buffer.from(padded, "base64").toString("binary");
//     const json = JSON.parse(decoded);
//     if (typeof json.user_id === "number") return json.user_id;
//     if (typeof json.user_id === "string" && /^\d+$/.test(json.user_id)) {
//       return Number(json.user_id);
//     }
//     return null;
//   } catch {
//     return null;
//   }
// }

// type SocketStatus = "connecting" | "connected" | "disconnected";
// type PeerJoinedStatus = boolean;

// type LiveSeshPartner = {
//   userId: number;
//   username: string | null;
//   friendId: number | null;
//   friendName: string | null;
// } | null;

// type GeckoCoordsMessage = {
//   from_user: number;
//   friend_id?: number;
//   position: [number, number];
// };

// type HostGeckoCoordsMessage = {
//   from_user: number;
//   friend_id?: number;
//   position: [number, number];
//   steps?: [number, number][];
//   first_fingers?: [number, number][];
//   held_moments?: number[] | Float32Array;
//   held_moments_len?: number;
//   moments?: number[][];
//   moments_len?: number;
//   timestamp?: number;
// };

// type GuestGeckoCoordsMessage = {
//   from_user: number;
//   position: [number, number];
//   steps?: [number, number][];
//   timestamp?: number;
// };

// type GeckoMessage = {
//   from_user: number;
//   message: string | null;
//   received_at: number;
// } | null;

// type ScoreState = {
//   user?: number;
//   total_steps_all_time?: number;
//   multiplier?: number;
//   expires_at?: string | null;
//   updated_on?: string | null;
//   base_multiplier?: number;
//   energy?: number;
//   surplus_energy?: number;
//   energy_updated_at?: string | null;
//   revives_at?: string | null;
//   recharge_per_second?: number;
//   streak_recharge_per_second?: number;
//   step_fatigue_per_step?: number;
//   streak_fatigue_multiplier?: number;
//   surplus_cap?: number;
//   personality_type?: number;
//   personality_type_label?: string;
//   memory_type?: number;
//   memory_type_label?: string;
//   active_hours_type?: number;
//   active_hours_type_label?: string;
//   story_type?: number;
//   story_type_label?: string;
//   stamina?: number;
//   max_active_hours?: number;
//   max_duration_till_revival?: number;
//   max_score_multiplier?: number;
//   max_streak_length_seconds?: number;
//   active_hours?: number[];
//   gecko_created_on?: string | null;
// };

// type UpdateGeckoDataPayload = {
//   event_type?: string;
//   steps?: number;
//   distance?: number;
//   started_on?: string;
//   ended_on?: string;
//   points_earned?: object[];
//   score_state?: {
//     multiplier?: number;
//     expiration_length?: number;
//   };
//   client_energy?: number;
//   client_surplus_energy?: number;
//   client_multiplier?: number;
//   client_computed_at?: string;
//   client_fatigue?: number;
//   client_recharge?: number;
// };

// type PeerGeckoPosition = {
//   from_user: number;
//   position: [number, number];
//   received_at: number;
// } | null;

// type HostCapsulesSV = {
//   from_user: number;
//   moments?: any[][];
//   moments_len?: number;
//   received_at: number;
// } | null;

// type HostPeerGeckoPosition = {
//   from_user: number;
//   position: [number, number];
//   steps?: [number, number][];
//   first_fingers?: [number, number][];
//   held_moments?: number[] | Float32Array;
//   held_moments_len?: number;
//   moments?: number[][];
//   moments_len?: number;
//   received_at: number;
// } | null;

// type HostCapsuleMoment = {
//   id: number;
//   coord: [number, number];
//   stored_index: number | null;
//   guest_progress?: number;
// };

// type GuestPeerGeckoPosition = {
//   from_user: number;
//   position: [number, number];
//   steps?: [number, number][];
//   received_at: number;
// } | null;

// type GeckoWinProposed = {
//   sender_user_id: number;
//   gecko_game_type?: number;
//   pending_id: number;
//   my_capsule_id?: string;
//   partner_capsule_id?: string;
//   received_at: number;
// };

// type EnergyState = {
//   energy: number;
//   surplusEnergy: number;
// };

// type CapsuleProgress = {
//   from_user?: number;
//   capsule_id: string;
//   new_progress: number;
//   received_at: number;
// } | null;

// type GeckoMatchWinNavigatePayload = {
//   pending_id: number;
//   sender_user_id?: number;
//   gecko_game_type?: number;
//   my_capsule_id?: string;
//   partner_capsule_id?: string;
//   received_at: number;
// };

// type GeckoMatchPendingAcceptPartnerPayload = {
//   pending_id: number;
//   match_key?: string;
//   accepted_by_user_id?: number;
// };

// type GeckoMatchFinalizedPayload = {
//   match_key?: string;
//   partner_user_id?: number;
// };

// type ForceDisconnectPayload = {
//   reason?: string;
// };

// type GeckoWebsocketContextValue = {
//   socketStatusSV: SharedValue<SocketStatus>;
//   peerJoinedStatusSV: SharedValue<PeerJoinedStatus>;
//   sharedColorLightSV: SharedValue;
//   sharedColorDarkSV: SharedValue;

//   scoreStateRef: React.MutableRefObject<ScoreState | null>;
//   liveSeshPartner: LiveSeshPartner;
//   energySV: SharedValue<EnergyState>;
//   peerGeckoPositionSV: SharedValue<PeerGeckoPosition>;
//   hostPeerGeckoPositionSV: SharedValue<HostPeerGeckoPosition>;
//   guestPeerGeckoPositionSV: SharedValue<GuestPeerGeckoPosition>;

//   hasReceivedInitialScoreStateRef: React.MutableRefObject<boolean>;
//   initialBackendEnergyUpdatedAtRef: React.MutableRefObject<string | null>;
//   latestBackendEnergyUpdatedAtRef: React.MutableRefObject<string | null>;
//   multiplierRef: React.MutableRefObject<number>;

//   geckoMessageSV: SharedValue<GeckoMessage>;

//   wsRef: React.MutableRefObject<WebSocket | null>;

//   connect: () => Promise<void>;
//   disconnect: () => void;
//   setWantsConnection: (wants: boolean) => void;

//   bindFriend: (
//     friendId: number,
//     friendLightColor: string,
//     friendDarkColor: string,
//   ) => boolean;
//   clearFriendBinding: () => boolean;
//   getFriendBindingState: () => {
//     isFriendBound: boolean;
//     pendingFriendId: number | null;
//     boundFriendId: number | null;
//   };

//   flush: () => void;
//   sendRaw: (
//     payload: object,
//     options?: { requireFriendBound?: boolean },
//   ) => boolean;

//   getScoreState: () => boolean;
//   getGeckoScreenPosition: () => boolean;
//   joinLiveSesh: () => boolean;
//   leaveLiveSesh: () => boolean;

//   updateGeckoData: (payload: UpdateGeckoDataPayload) => boolean;

//   sendGeckoPosition: (position: [number, number], force?: boolean) => boolean;

//   sendHostGeckoPosition: (
//     position: [number, number],
//     steps?: [number, number][],
//     first_fingers?: [number, number][],
//     held_moments?: Float32Array | number[] | null,
//     moments?: {
//       id: number;
//       coord: [number, number];
//       stored_index: number;
//     }[],
//     force?: boolean,
//   ) => boolean;

//   sendGuestGeckoPosition: (
//     position: [number, number],
//     force?: boolean,
//   ) => boolean;

//   registerOnScoreState: (cb: (data: ScoreState) => void) => void;
//   registerOnSync: (cb: () => void) => void;
//   registerOnGeckoCoords: (cb: (data: GeckoCoordsMessage) => void) => void;
//   registerOnHostGeckoCoords: (
//     cb: (data: HostGeckoCoordsMessage) => void,
//   ) => void;
//   registerOnGuestGeckoCoords: (
//     cb: (data: GuestGeckoCoordsMessage) => void,
//   ) => void;
//   registerOnJoinLiveSesh: (cb: (partnerId: number | null) => void) => void;
//   registerOnLeaveLiveSesh: (cb: () => void) => void;
//   registerOnLiveSeshCancelled: (cb: (data: any) => void) => void;
//   registerOnGeckoMessage: (
//     cb: (data: { from_user: number; message: string | null }) => void,
//   ) => void;

//   requestPresenceStatus: () => boolean;
//   sendReadStatusToGecko: (messageCode: 0 | 1 | 2) => boolean;
//   sendFETextToGecko: (message: string) => boolean;

//   proposeGeckoWin: (capsuleId: string) => boolean;
//   registerOnGeckoWinProposed: (cb: (data: GeckoWinProposed) => void) => void;
//   registerOnGeckoMatchWinNavigate: (
//     cb: (data: GeckoMatchWinNavigatePayload) => void,
//   ) => void;
//   registerOnGeckoMatchPendingAcceptPartner: (
//     cb: (data: GeckoMatchPendingAcceptPartnerPayload) => void,
//   ) => void;
//   registerOnGeckoMatchFinalized: (
//     cb: (data: GeckoMatchFinalizedPayload) => void,
//   ) => void;
//   registerOnForceDisconnect: (cb: (data: ForceDisconnectPayload) => void) => void;

//   registerOnRemoveCapsule: (capsuleId: string) => void;
//   onRemoveCapsuleRef: React.MutableRefObject<string>;
//   sendCapsuleProgress: (capsule_id: string, new_progress: number) => boolean;
//   capsuleProgressSV: SharedValue<CapsuleProgress>;
//   sendAllHostCapsules: (moments?: HostCapsuleMoment[]) => boolean;
// };

// const GeckoWebsocketContext = createContext<GeckoWebsocketContextValue | null>(
//   null,
// );

// type ProviderProps = {
//   children: React.ReactNode;
// };

// export const GeckoWebsocketProvider = ({ children }: ProviderProps) => {
//   const [liveSeshPartner, setLiveSeshPartner] = useState<LiveSeshPartner>(null);

//   const socketStatusSV = useSharedValue<SocketStatus>("disconnected");
//   const peerJoinedStatusSV = useSharedValue<PeerJoinedStatus>(false);

//   const sharedColorDarkSV = useSharedValue(manualGradientColors.darkColor);
//   const sharedColorLightSV = useSharedValue(manualGradientColors.lightColor);

//   const capsuleProgressSV = useSharedValue<CapsuleProgress>(null);

//   const geckoMessageSV = useSharedValue<GeckoMessage>(null);

//   const wsRef = useRef<WebSocket | null>(null);
//   const scoreStateRef = useRef<ScoreState | null>(null);

//   const pendingFriendIdRef = useRef<number | null>(null);
//   const pendingFriendLightColorRef = useRef<string | null>(null);
//   const pendingFriendDarkColorRef = useRef<string | null>(null);
//   const boundFriendIdRef = useRef<number | null>(null);
//   const isFriendBoundRef = useRef(false);

//   const matchesRef = useRef(false);
//   const matchesSV = useSharedValue([]);

//   const onScoreStateRef = useRef<((data: ScoreState) => void) | null>(null);
//   const onSyncRef = useRef<(() => void) | null>(null);
//   const onGeckoCoordsRef = useRef<((data: GeckoCoordsMessage) => void) | null>(
//     null,
//   );
//   const onHostGeckoCoordsRef = useRef<
//     ((data: HostGeckoCoordsMessage) => void) | null
//   >(null);
//   const onGuestGeckoCoordsRef = useRef<
//     ((data: GuestGeckoCoordsMessage) => void) | null
//   >(null);
//   const onCapsuleProgressRef = useRef<
//     | ((data: {
//         capsule_id: string;
//         new_progress: number;
//         from_user?: number;
//       }) => void)
//     | null
//   >(null);
//   const onJoinLiveSeshRef = useRef<((partnerId: number | null) => void) | null>(
//     null,
//   );
//   const onLeaveLiveSeshRef = useRef<(() => void) | null>(null);
//   const onLiveSeshCancelledRef = useRef<((data: any) => void) | null>(null);
//   const onGeckoMessageRef = useRef<
//     ((d: { from_user: number; message: string | null }) => void) | null
//   >(null);

//   const peerGeckoPositionSV = useSharedValue<PeerGeckoPosition>(null);
//   const hostPeerGeckoPositionSV = useSharedValue<HostPeerGeckoPosition>(null);

//   const hostCapsulesSV = useSharedValue<{
//     from_user: number;
//     moments: any[][];
//     moments_len: number;
//     received_at: number;
//   } | null>(null);

//   const guestPeerGeckoPositionSV = useSharedValue<GuestPeerGeckoPosition>(null);

//   const onGeckoWinProposedRef = useRef<((d: GeckoWinProposed) => void) | null>(
//     null,
//   );
//   const onGeckoMatchWinNavigateRef = useRef<
//     ((d: GeckoMatchWinNavigatePayload) => void) | null
//   >(null);
//   const onGeckoMatchPendingAcceptPartnerRef = useRef<
//     ((d: GeckoMatchPendingAcceptPartnerPayload) => void) | null
//   >(null);
//   const onGeckoMatchFinalizedRef = useRef<
//     ((d: GeckoMatchFinalizedPayload) => void) | null
//   >(null);
//   const onForceDisconnectRef = useRef<
//     ((d: ForceDisconnectPayload) => void) | null
//   >(null);

//   const onRemoveCapsuleRef = useRef<((capsuleId: string) => void) | null>(null);

//   const energySV = useSharedValue<EnergyState>({
//     energy: 1.0,
//     surplusEnergy: 0.0,
//   });

//   const pendingDataActionsRef = useRef<
//     (UpdateGeckoDataPayload & { friend_id: number })[]
//   >([]);

//   const reconnectTimeoutRef = useRef<ReturnType<typeof setTimeout> | null>(
//     null,
//   );
//   const flushIntervalRef = useRef<ReturnType<typeof setInterval> | null>(null);
//   const pingIntervalRef = useRef<ReturnType<typeof setInterval> | null>(null);
//   const PING_INTERVAL_MS = 3000;
//   const shouldReconnectRef = useRef(true);
//   const wantsConnectionRef = useRef(false);

//   const hasReceivedInitialScoreStateRef = useRef(false);
//   const initialBackendEnergyUpdatedAtRef = useRef<string | null>(null);
//   const latestBackendEnergyUpdatedAtRef = useRef<string | null>(null);

//   const streakExpiryTimeoutRef = useRef<ReturnType<typeof setTimeout> | null>(
//     null,
//   );
//   const multiplierRef = useRef(1);

//   const lastSentGeckoPositionAtRef = useRef(0);
//   const lastSentHostGeckoPositionAtRef = useRef(0);
//   const lastSentGuestGeckoPositionAtRef = useRef(0);

//   const stepsScratchRef = useRef<number[][]>([
//     [0, 0],
//     [0, 0],
//     [0, 0],
//     [0, 0],
//   ]);

//   const firstFingersScratchRef = useRef<number[][]>([
//     [0, 0],
//     [0, 0],
//     [0, 0],
//     [0, 0],
//   ]);

//   const momentsScratchRef = useRef<number[][]>(
//     Array.from({ length: 30 }, () => [0, 0, 0, 0, 0]),
//   );

//   const heldScratchRef = useRef(new Float32Array(8));

//   const FLUSH_INTERVAL_MS = 20000;
//   const GECKO_POSITION_THROTTLE_MS = 50;

//   const registerOnGeckoWinProposed = useCallback(
//     (cb: (d: GeckoWinProposed) => void) => {
//       onGeckoWinProposedRef.current = cb;
//     },
//     [],
//   );

//   const registerOnGeckoMatchWinNavigate = useCallback(
//     (cb: (d: GeckoMatchWinNavigatePayload) => void) => {
//       onGeckoMatchWinNavigateRef.current = cb;
//     },
//     [],
//   );

//   const registerOnGeckoMatchPendingAcceptPartner = useCallback(
//     (cb: (d: GeckoMatchPendingAcceptPartnerPayload) => void) => {
//       onGeckoMatchPendingAcceptPartnerRef.current = cb;
//     },
//     [],
//   );

//   const registerOnGeckoMatchFinalized = useCallback(
//     (cb: (d: GeckoMatchFinalizedPayload) => void) => {
//       onGeckoMatchFinalizedRef.current = cb;
//     },
//     [],
//   );

//   const registerOnForceDisconnect = useCallback(
//     (cb: (d: ForceDisconnectPayload) => void) => {
//       onForceDisconnectRef.current = cb;
//     },
//     [],
//   );

//   const onPeerPresenceRef = useRef<((online: boolean) => void) | null>(null);

//   const registerOnPeerPresence = useCallback(
//     (cb: (online: boolean) => void) => {
//       onPeerPresenceRef.current = cb;

//       return () => {
//         if (onPeerPresenceRef.current === cb) {
//           onPeerPresenceRef.current = null;
//         }
//       };
//     },
//     [],
//   );

//   const registerOnRemoveCapsule = useCallback(
//     (cb: (capsuleId: string) => void) => {
//       onRemoveCapsuleRef.current = cb;

//       return () => {
//         if (onRemoveCapsuleRef.current === cb) {
//           onRemoveCapsuleRef.current = null;
//         }
//       };
//     },
//     [],
//   );
//   const registerOnScoreState = useCallback((cb: (data: ScoreState) => void) => {
//     onScoreStateRef.current = cb;
//   }, []);

//   const registerOnGeckoMessage = useCallback(
//     (cb: (d: { from_user: number; message: string | null }) => void) => {
//       onGeckoMessageRef.current = cb;
//     },
//     [],
//   );

//   const registerOnSync = useCallback((cb: () => void) => {
//     onSyncRef.current = cb;
//   }, []);

//   const registerOnGeckoCoords = useCallback(
//     (cb: (data: GeckoCoordsMessage) => void) => {
//       onGeckoCoordsRef.current = cb;
//     },
//     [],
//   );

//   const registerOnHostGeckoCoords = useCallback(
//     (cb: (data: HostGeckoCoordsMessage) => void) => {
//       onHostGeckoCoordsRef.current = cb;
//     },
//     [],
//   );

//   const registerOnGuestGeckoCoords = useCallback(
//     (cb: (data: GuestGeckoCoordsMessage) => void) => {
//       onGuestGeckoCoordsRef.current = cb;
//     },
//     [],
//   );

//   const registerOnCapsuleProgress = useCallback(
//     (
//       cb: (data: {
//         capsule_id: string;
//         new_progress: number;
//         from_user?: number;
//       }) => void,
//     ) => {
//       onCapsuleProgressRef.current = cb;

//       return () => {
//         if (onCapsuleProgressRef.current === cb) {
//           onCapsuleProgressRef.current = null;
//         }
//       };
//     },
//     [],
//   );

//   const registerOnJoinLiveSesh = useCallback(
//     (cb: (partnerId: number | null) => void) => {
//       onJoinLiveSeshRef.current = cb;
//     },
//     [],
//   );

//   const registerOnLeaveLiveSesh = useCallback((cb: () => void) => {
//     onLeaveLiveSeshRef.current = cb;
//   }, []);

//   const registerOnLiveSeshCancelled = useCallback((cb: (data: any) => void) => {
//     onLiveSeshCancelledRef.current = cb;
//   }, []);

//   const getFriendBindingState = useCallback(
//     () => ({
//       isFriendBound: isFriendBoundRef.current,
//       pendingFriendId: pendingFriendIdRef.current,
//       boundFriendId: boundFriendIdRef.current,
//     }),
//     [],
//   );

//   const publishScoreState = useCallback(
//     (data: ScoreState) => {
//       scoreStateRef.current = data;

//       energySV.value = {
//         energy: data?.energy ?? 1.0,
//         surplusEnergy: data?.surplus_energy ?? 0.0,
//       };

//       if (streakExpiryTimeoutRef.current) {
//         clearTimeout(streakExpiryTimeoutRef.current);
//         streakExpiryTimeoutRef.current = null;
//       }

//       const multiplier = data?.multiplier ?? 1;
//       const baseMultiplier = data?.base_multiplier ?? 1;
//       const expired =
//         !data?.expires_at || new Date(data.expires_at).getTime() <= Date.now();

//       multiplierRef.current = expired ? 1 : multiplier;

//       if (data?.expires_at && multiplier > baseMultiplier && !expired) {
//         const msUntilExpiry = new Date(data.expires_at).getTime() - Date.now();

//         if (msUntilExpiry > 0) {
//           streakExpiryTimeoutRef.current = setTimeout(() => {
//             streakExpiryTimeoutRef.current = null;
//             multiplierRef.current = 1;

//             console.log("gecko streak expired — requesting fresh score state");

//             if (wsRef.current?.readyState === WebSocket.OPEN) {
//               wsRef.current.send(JSON.stringify({ action: "get_score_state" }));
//             }
//           }, msUntilExpiry);
//         }
//       }

//       onScoreStateRef.current?.(data);
//     },
//     [energySV],
//   );

//   const stopFlushInterval = useCallback(() => {
//     if (flushIntervalRef.current) {
//       clearInterval(flushIntervalRef.current);
//       flushIntervalRef.current = null;
//     }
//   }, []);

//   const sendSetFriend = useCallback(
//     (
//       fid: number | null,
//       fLightColor: string | null,
//       fDarkColor: string | null,
//     ) => {
//       if (wsRef.current?.readyState !== WebSocket.OPEN || fid == null) {
//         return false;
//       }

//       wsRef.current.send(
//         JSON.stringify({
//           action: "set_friend",
//           data: {
//             friend_id: fid,
//             friend_light_color: fLightColor,
//             friend_dark_color: fDarkColor,
//           },
//         }),
//       );

//       return true;
//     },
//     [],
//   );

//   const sendRaw = useCallback(
//     (payload: object, options?: { requireFriendBound?: boolean }) => {
//       const requireFriendBound = options?.requireFriendBound ?? false;

//       if (wsRef.current?.readyState !== WebSocket.OPEN) {
//         return false;
//       }

//       if (requireFriendBound && !isFriendBoundRef.current) {
//         return false;
//       }

//       wsRef.current.send(JSON.stringify(payload));
//       return true;
//     },
//     [],
//   );

//   const flush = useCallback(() => {
//     if (wsRef.current?.readyState === WebSocket.OPEN) {
//       wsRef.current.send(JSON.stringify({ action: "flush" }));
//     }
//   }, []);

//   const startFlushInterval = useCallback(() => {
//     stopFlushInterval();

//     flushIntervalRef.current = setInterval(() => {
//       if (wsRef.current?.readyState === WebSocket.OPEN) {
//         onSyncRef.current?.();
//         flush();
//       }
//     }, FLUSH_INTERVAL_MS);
//   }, [flush, stopFlushInterval]);

//   const stopPingInterval = useCallback(() => {
//     if (pingIntervalRef.current) {
//       clearInterval(pingIntervalRef.current);
//       pingIntervalRef.current = null;
//     }
//   }, []);

//   const startPingInterval = useCallback(() => {
//     stopPingInterval();

//     pingIntervalRef.current = setInterval(() => {
//       if (wsRef.current?.readyState === WebSocket.OPEN) {
//         wsRef.current.send(JSON.stringify({ action: "ping" }));
//       }
//     }, PING_INTERVAL_MS);
//   }, [stopPingInterval]);

//   const getScoreState = useCallback(() => {
//     if (wsRef.current?.readyState !== WebSocket.OPEN) {
//       return false;
//     }

//     wsRef.current.send(JSON.stringify({ action: "get_score_state" }));
//     return true;
//   }, []);

//   const getGeckoScreenPosition = useCallback(() => {
//     if (wsRef.current?.readyState !== WebSocket.OPEN) {
//       return false;
//     }

//     wsRef.current.send(JSON.stringify({ action: "get_gecko_screen_position" }));
//     return true;
//   }, []);

//   const joinLiveSesh = useCallback(() => {
//     if (wsRef.current?.readyState !== WebSocket.OPEN) {
//       return false;
//     }

//     wsRef.current.send(JSON.stringify({ action: "join_live_sesh" }));
//     return true;
//   }, []);

//   const leaveLiveSesh = useCallback(() => {
//     if (wsRef.current?.readyState !== WebSocket.OPEN) {
//       return false;
//     }

//     wsRef.current.send(JSON.stringify({ action: "leave_live_sesh" }));
//     return true;
//   }, []);

//   const requestPresenceStatus = useCallback(() => {
//     if (wsRef.current?.readyState !== WebSocket.OPEN) {
//       return false;
//     }

//     peerJoinedStatusSV.value = false;

//     sharedColorLightSV.value = manualGradientColors.lightColor;
//     sharedColorDarkSV.value = manualGradientColors.darkColor;

//     wsRef.current.send(JSON.stringify({ action: "request_peer_presence" }));
//     return true;
//   }, [peerJoinedStatusSV, sharedColorLightSV, sharedColorDarkSV]);

//   const sendReadStatusToGecko = useCallback((messageCode: 0 | 1 | 2) => {
//     console.log("sending read status?");

//     if (wsRef.current?.readyState !== WebSocket.OPEN) {
//       return false;
//     }

//     wsRef.current.send(
//       JSON.stringify({
//         action: "send_read_status_to_gecko",
//         data: { message_code: messageCode },
//       }),
//     );

//     return true;
//   }, []);

//   const sendFETextToGecko = useCallback((message: string) => {
//     if (wsRef.current?.readyState !== WebSocket.OPEN) {
//       return false;
//     }

//     wsRef.current.send(
//       JSON.stringify({
//         action: "send_front_end_text_to_gecko",
//         data: { message },
//       }),
//     );

//     return true;
//   }, []);

//   const flushPendingUpdateGeckoData = useCallback(() => {
//     if (
//       wsRef.current?.readyState !== WebSocket.OPEN ||
//       !isFriendBoundRef.current
//     ) {
//       return;
//     }

//     if (pendingDataActionsRef.current.length === 0) {
//       return;
//     }

//     const queued = [...pendingDataActionsRef.current];
//     pendingDataActionsRef.current = [];

//     queued.forEach((payload) => {
//       wsRef.current?.send(
//         JSON.stringify({
//           action: "update_gecko_data",
//           data: payload,
//         }),
//       );
//     });
//   }, []);

//   const bindFriend = useCallback(
//     (friendId: number, friendLightColor: string, friendDarkColor: string) => {
//       if (boundFriendIdRef.current === friendId && isFriendBoundRef.current) {
//         return true;
//       }

//       if (pendingFriendIdRef.current === friendId) {
//         return wsRef.current?.readyState === WebSocket.OPEN;
//       }

//       pendingFriendIdRef.current = friendId;
//       pendingFriendLightColorRef.current = friendLightColor;
//       pendingFriendDarkColorRef.current = friendDarkColor;
//       isFriendBoundRef.current = false;
//       boundFriendIdRef.current = null;

//       peerGeckoPositionSV.value = null;
//       hostPeerGeckoPositionSV.value = null;
//       guestPeerGeckoPositionSV.value = null;

//       if (wsRef.current?.readyState === WebSocket.OPEN) {
//         return sendSetFriend(friendId, friendLightColor, friendDarkColor);
//       }

//       return false;
//     },
//     [
//       guestPeerGeckoPositionSV,
//       hostPeerGeckoPositionSV,
//       peerGeckoPositionSV,
//       sendSetFriend,
//     ],
//   );

//   const clearFriendBinding = useCallback(() => {
//     pendingFriendIdRef.current = null;
//     isFriendBoundRef.current = false;
//     boundFriendIdRef.current = null;
//     pendingDataActionsRef.current = [];

//     peerGeckoPositionSV.value = null;
//     hostPeerGeckoPositionSV.value = null;
//     guestPeerGeckoPositionSV.value = null;

//     return true;
//   }, [guestPeerGeckoPositionSV, hostPeerGeckoPositionSV, peerGeckoPositionSV]);

//   const updateGeckoData = useCallback(
//     (payload: UpdateGeckoDataPayload) => {
//       const fid = boundFriendIdRef.current ?? pendingFriendIdRef.current;

//       if (fid == null) {
//         console.log("[WS] updateGeckoData skipped — no friend binding");
//         return false;
//       }

//       const full: UpdateGeckoDataPayload & { friend_id: number } = {
//         ...payload,
//         friend_id: fid,
//         client_energy:
//           typeof payload.client_energy === "number"
//             ? payload.client_energy
//             : energySV.value.energy,
//         client_surplus_energy:
//           typeof payload.client_surplus_energy === "number"
//             ? payload.client_surplus_energy
//             : energySV.value.surplusEnergy,
//         client_multiplier:
//           typeof payload.client_multiplier === "number"
//             ? payload.client_multiplier
//             : (scoreStateRef.current?.multiplier ?? undefined),
//         client_computed_at:
//           payload.client_computed_at ?? new Date().toISOString(),
//       };

//       if (
//         wsRef.current?.readyState === WebSocket.OPEN &&
//         isFriendBoundRef.current
//       ) {
//         wsRef.current.send(
//           JSON.stringify({ action: "update_gecko_data", data: full }),
//         );
//         return true;
//       }

//       pendingDataActionsRef.current.push(full);
//       return false;
//     },
//     [energySV],
//   );

//   const sendGeckoPosition = useCallback(
//     (position: [number, number], force = false) => {
//       const now = Date.now();

//       if (!isFriendBoundRef.current) {
//         return false;
//       }

//       if (
//         !force &&
//         now - lastSentGeckoPositionAtRef.current < GECKO_POSITION_THROTTLE_MS
//       ) {
//         return false;
//       }

//       lastSentGeckoPositionAtRef.current = now;

//       if (wsRef.current?.readyState !== WebSocket.OPEN) {
//         return false;
//       }

//       wsRef.current.send(
//         notepack.encode({
//           action: "update_gecko_position",
//           data: { position },
//         }),
//       );

//       return true;
//     },
//     [],
//   );

//   const sendHostGeckoPosition = useCallback(
//     (
//       position: [number, number],
//       steps: [number, number][] = [],
//       first_fingers: [number, number][] = [],
//       held_moments: Float32Array | number[] | null = null,
//       moments: {
//         id: number;
//         coord: [number, number];
//         stored_index: number;
//       }[] = [],
//       force = false,
//     ) => {
//       const now = Date.now();

//       if (!isFriendBoundRef.current) {
//         return false;
//       }

//       if (
//         !force &&
//         now - lastSentHostGeckoPositionAtRef.current <
//           GECKO_POSITION_THROTTLE_MS
//       ) {
//         return false;
//       }

//       lastSentHostGeckoPositionAtRef.current = now;

//       if (wsRef.current?.readyState !== WebSocket.OPEN) {
//         return false;
//       }

//       const stepsScratch = stepsScratchRef.current;
//       const stepsLen = Math.min(steps.length, stepsScratch.length);

//       for (let i = 0; i < stepsLen; i++) {
//         stepsScratch[i][0] = steps[i][0];
//         stepsScratch[i][1] = steps[i][1];
//       }

//       const firstFingersScratch = firstFingersScratchRef.current;
//       const firstFingersLen = Math.min(
//         first_fingers.length,
//         firstFingersScratch.length,
//       );

//       for (let i = 0; i < firstFingersLen; i++) {
//         firstFingersScratch[i][0] = first_fingers[i][0];
//         firstFingersScratch[i][1] = first_fingers[i][1];
//       }

//       const momentsScratch = momentsScratchRef.current;
//       const momentsLen = Math.min(moments.length, momentsScratch.length);

//       for (let i = 0; i < momentsLen; i++) {
//         const m = moments[i];
//         momentsScratch[i][0] = m.id;
//         momentsScratch[i][1] = m.coord[0];
//         momentsScratch[i][2] = m.coord[1];
//         momentsScratch[i][3] = m.stored_index;
//         momentsScratch[i][4] = (m as any).guest_progress ?? 0;
//       }

//       const heldScratch = heldScratchRef.current;
//       const heldLen = 8;

//       if (held_moments) {
//         const copiedHeldLen = Math.min(held_moments.length, heldScratch.length);

//         for (let i = 0; i < copiedHeldLen; i++) {
//           heldScratch[i] = held_moments[i];
//         }
//       }

//       wsRef.current.send(
//         notepack.encode({
//           action: "update_host_gecko_position",
//           data: {
//             position,
//             steps: stepsScratch,
//             steps_len: stepsLen,
//             first_fingers: firstFingersScratch,
//             held_moments: heldScratch,
//             held_moments_len: heldLen,
//             moments: momentsScratch,
//             moments_len: momentsLen,
//             timestamp: now,
//           },
//         }),
//       );

//       return true;
//     },
//     [],
//   );

//   const sendAllHostCapsules = useCallback(
//     (moments: HostCapsuleMoment[] = []) => {
//       if (wsRef.current?.readyState !== WebSocket.OPEN) {
//         return false;
//       }

//       if (!isFriendBoundRef.current) {
//         console.log("not sending because friend bound ref doesnt exist");
//         return false;
//       }

//       const now = Date.now();

//       const momentsScratch = momentsScratchRef.current;
//       const momentsLen = Math.min(moments.length, momentsScratch.length);

//       for (let i = 0; i < momentsLen; i++) {
//         const m = moments[i];

//         momentsScratch[i][0] = m.id;
//         momentsScratch[i][1] = m.coord?.[0] ?? 0.5;
//         momentsScratch[i][2] = m.coord?.[1] ?? 0.5;
//         momentsScratch[i][3] = m.stored_index ?? -1;
//         momentsScratch[i][4] = m.guest_progress ?? 0;
//       }

//       wsRef.current.send(
//         notepack.encode({
//           action: "send_all_host_capsules",
//           data: {
//             moments: momentsScratch,
//             moments_len: momentsLen,
//             timestamp: now,
//           },
//         }),
//       );

//       return true;
//     },
//     [],
//   );

//   const sendCapsuleProgress = useCallback(
//     ({
//       capsule_id,
//       new_progress,
//     }: {
//       capsule_id: string;
//       new_progress: number;
//     }) => {
//       if (wsRef.current?.readyState !== WebSocket.OPEN) {
//         return false;
//       }

//       const now = Date.now();

//       wsRef.current.send(
//         notepack.encode({
//           action: "update_capsule_progress",
//           data: { capsule_id, new_progress, timestamp: now },
//         }),
//       );
//       console.log("SENDING PROGRESS OVER SOCKET");
//       return true;
//     },
//     [],
//   );

//   // FIX: was 'resync_capsule_matches' (unknown action). Both backends accept
//   // 'repull_capsule_matches' for a fresh DB-backed match recompute.
//   const repullCapsuleMatches = useCallback(() => {
//     if (wsRef.current?.readyState !== WebSocket.OPEN) return false;
//     wsRef.current.send(JSON.stringify({ action: "repull_capsule_matches" }));
//     return true;
//   }, []);

//   const sendMatchRequest = useCallback((geckoGameType: number) => {
//     console.log(`gecko game type sending: `, geckoGameType);
//     if (wsRef.current?.readyState !== WebSocket.OPEN) return false;
//     wsRef.current.send(
//       JSON.stringify({
//         action: "send_match_request",
//         data: { gecko_game_type: geckoGameType },
//       }),
//     );
//     return true;
//   }, []);

//   const proposeGeckoWin = useCallback((capsuleId: string) => {
//     if (wsRef.current?.readyState !== WebSocket.OPEN) return false;

//     console.log("sending propseGeckoWin in socket: ", capsuleId);

//     wsRef.current.send(
//       JSON.stringify({
//         action: "propose_gecko_win",
//         data: { capsule_id: capsuleId },
//       }),
//     );
//     return true;
//   }, []);

//   const proposeGeckoMatchWin = useCallback((geckoGameType: number) => {
//     console.log(`gecko game type sending: `, geckoGameType);
//     if (wsRef.current?.readyState !== WebSocket.OPEN) return false;
//     wsRef.current.send(
//       JSON.stringify({
//         action: "propose_gecko_match_win",
//         data: { gecko_game_type: geckoGameType },
//       }),
//     );
//     return true;
//   }, []);

//   const sendGuestGeckoPosition = useCallback(
//     (position: [number, number], force = false) => {
//       const now = Date.now();

//       if (
//         !force &&
//         now - lastSentGuestGeckoPositionAtRef.current <
//           GECKO_POSITION_THROTTLE_MS
//       ) {
//         return false;
//       }

//       lastSentGuestGeckoPositionAtRef.current = now;

//       if (wsRef.current?.readyState !== WebSocket.OPEN) {
//         return false;
//       }

//       wsRef.current.send(
//         notepack.encode({
//           action: "update_guest_gecko_position",
//           data: { position, timestamp: now },
//         }),
//       );

//       return true;
//     },
//     [],
//   );

//   const clearReconnectTimeout = useCallback(() => {
//     if (reconnectTimeoutRef.current) {
//       clearTimeout(reconnectTimeoutRef.current);
//       reconnectTimeoutRef.current = null;
//     }
//   }, []);

//   const disconnect = useCallback(() => {
//     shouldReconnectRef.current = false;
//     clearReconnectTimeout();
//     stopFlushInterval();
//     stopPingInterval();

//     if (streakExpiryTimeoutRef.current) {
//       clearTimeout(streakExpiryTimeoutRef.current);
//       streakExpiryTimeoutRef.current = null;
//     }

//     if (wsRef.current?.readyState === WebSocket.OPEN) {
//       wsRef.current.send(JSON.stringify({ action: "flush" }));
//       wsRef.current.send(JSON.stringify({ action: "leave_live_sesh" }));
//     }

//     if (wsRef.current) {
//       wsRef.current.onclose = null;
//       wsRef.current.close();
//       wsRef.current = null;
//     }

//     socketStatusSV.value = "disconnected";

//     isFriendBoundRef.current = false;
//     boundFriendIdRef.current = null;
//     pendingFriendIdRef.current = null;

//     setLiveSeshPartner(null);
//   }, [clearReconnectTimeout, socketStatusSV, stopFlushInterval, stopPingInterval]);

//   const connect = useCallback(async () => {
//     console.log(
//       "starting connect..................................................",
//     );

//     shouldReconnectRef.current = true;
//     clearReconnectTimeout();

//     if (wsRef.current?.readyState === WebSocket.OPEN) {
//       console.log("[WS] connect() skipped — socket already OPEN");
//       return;
//     }

//     if (wsRef.current?.readyState === WebSocket.CONNECTING) {
//       console.log("[WS] connect() skipped — socket already CONNECTING");
//       return;
//     }

//     if (wsRef.current) {
//       wsRef.current.onclose = null;
//       wsRef.current.close();
//       wsRef.current = null;
//     }

//     const token = await SecureStore.getItemAsync("accessToken");

//     if (!token) {
//       socketStatusSV.value = "disconnected";
//       return;
//     }

//     // Rust socket auth: extract user_id from the JWT we already have.
//     // NOTE: the Rust server currently trusts this query param. Validate
//     // tokens server-side before opening this URL to the public internet.
//     const userId = decodeJwtUserId(token);
//     if (userId == null) {
//       console.log("[WS] could not extract user_id from token — abort connect");
//       socketStatusSV.value = "disconnected";
//       return;
//     }

//     socketStatusSV.value = "connecting";

//     isFriendBoundRef.current = false;
//     boundFriendIdRef.current = null;

//     const url = `${RUST_SOCKET_HOST}${RUST_SOCKET_PATH}?user_id=${userId}`;
//     const ws = new WebSocket(url);
//     ws.binaryType = "arraybuffer";

//     ws.onopen = () => {
//       socketStatusSV.value = "connected";
//       startFlushInterval();
//       startPingInterval();

//       const fid = pendingFriendIdRef.current;
//       const fLightColor = pendingFriendLightColorRef.current;
//       const fDarkColor = pendingFriendDarkColorRef.current;

//       if (fid != null) {
//         sendSetFriend(fid, fLightColor, fDarkColor);
//         console.log("sending friend");
//       } else {
//         // Rust sends an initial score_state right after the connect-handshake
//         // (it ships in the hydrate response), so we don't strictly need to
//         // ask for it here — but doing so is harmless and matches the
//         // previous channels behavior on slow first paints.
//         getScoreState();
//         getGeckoScreenPosition();
//         console.log("join sessionnnn");
//         joinLiveSesh();
//       }
//     };

//     ws.onmessage = (event) => {
//       let message: any;

//       try {
//         if (event.data instanceof ArrayBuffer) {
//           message = notepack.decode(new Uint8Array(event.data));
//         } else {
//           message = JSON.parse(event.data);
//         }
//       } catch (error) {
//         console.log("[WS] failed to decode message", error);
//         return;
//       }

//       // Rust evicts older sockets when a new connection for the same user
//       // arrives. If we don't bail out of the reconnect loop we'll fight
//       // the new tab/device forever.
//       if (message.action === "force_disconnect") {
//         console.log("[WS] force_disconnect", message.data);
//         shouldReconnectRef.current = false;
//         wantsConnectionRef.current = false;
//         onForceDisconnectRef.current?.(message.data ?? {});
//         return;
//       }

//       // Rust handshake ack — informational only.
//       if (message.action === "rust_connected") {
//         console.log("[WS] rust_connected", message.data);
//         return;
//       }

//       if (message.action === "set_friend_ok") {
//         const fid = message.data?.friend_id ?? null;

//         console.log("[WS] set_friend_ok", fid);

//         isFriendBoundRef.current = true;
//         boundFriendIdRef.current = fid;
//         pendingFriendIdRef.current = null;

//         getScoreState();
//         getGeckoScreenPosition();
//         joinLiveSesh();
//         flushPendingUpdateGeckoData();
//         return;
//       }

//       if (message.action === "capsule_matches_ready") {
//         console.log("[WS] capsule_matches_ready", message.data);
//         matchesSV.value = message.data?.matches ?? [];
//         return;
//       }

//       if (message.action === "match_request_result") {
//         console.log("[WS] match_request_result", message.data);
//         return;
//       }

//       if (message.action === "send_match_request_failed") {
//         console.log("[WS] send_match_request_failed", message.data);
//         return;
//       }

//       if (message.action === "set_friend_failed") {
//         console.log("[WS] set_friend_failed", message.data);

//         isFriendBoundRef.current = false;
//         boundFriendIdRef.current = null;
//         return;
//       }

//       if (message.action === "peer_presence") {
//         console.log(`PEER PRESENCE!`, message.data);
//         const online = message.data?.online ?? false;
//         peerJoinedStatusSV.value = online;
//         onPeerPresenceRef.current?.(online);

//         const light =
//           message.data?.friend_light_color ?? manualGradientColors.lightColor;

//         const dark =
//           message.data?.friend_dark_color ?? manualGradientColors.darkColor;

//         sharedColorLightSV.value = light;
//         sharedColorDarkSV.value = dark;

//         return;
//       }

//       if (message.action === "gecko_win_proposed") {
//         console.log("[WS] gecko_win_proposed", message.data);

//         const pendingIdRaw = message.data?.pending_id;
//         const pendingId = Number(pendingIdRaw);
//         const receivedAt = performance.now();

//         if (pendingIdRaw != null && Number.isFinite(pendingId)) {
//           onGeckoMatchWinNavigateRef.current?.({
//             pending_id: pendingId,
//             sender_user_id: message.data?.sender_user_id,
//             gecko_game_type: message.data?.gecko_game_type,
//             my_capsule_id: message.data?.my_capsule_id,
//             partner_capsule_id: message.data?.partner_capsule_id,
//             received_at: receivedAt,
//           });
//         } else {
//           onGeckoWinProposedRef.current?.({
//             sender_user_id: message.data?.sender_user_id,
//             gecko_game_type: message.data?.gecko_game_type,
//             pending_id: pendingId,
//             my_capsule_id: message.data?.my_capsule_id,
//             partner_capsule_id: message.data?.partner_capsule_id,
//             received_at: receivedAt,
//           });
//         }

//         return;
//       }

//       if (message.action === "propose_gecko_win_ok") {
//         console.log("[WS] propose_gecko_win_ok", message.data);
//         return;
//       }

//       if (message.action === "propose_gecko_match_win_ok") {
//         console.log("[WS] propose_gecko_match_win_ok", message.data);
//         return;
//       }

//       if (message.action === "propose_gecko_win_failed") {
//         console.log("[WS] propose_gecko_win_failed", message.data);
//         return;
//       }

//       if (message.action === "propose_gecko_match_win_failed") {
//         console.log("[WS] propose_gecko_match_win_failed", message.data);
//         return;
//       }

//       // Pushed when the *partner* of a match proposal accepts. The current
//       // user still needs to accept on their side.
//       if (message.action === "gecko_win_match_pending_accept_partner") {
//         console.log("[WS] gecko_win_match_pending_accept_partner", message.data);
//         const pendingId = Number(message.data?.pending_id);
//         onGeckoMatchPendingAcceptPartnerRef.current?.({
//           pending_id: pendingId,
//           match_key: message.data?.match_key,
//           accepted_by_user_id: message.data?.accepted_by_user_id,
//         });
//         return;
//       }

//       // Pushed once both sides have accepted — source capsules are gone,
//       // FE should refetch / clear cached match data.
//       if (message.action === "gecko_win_match_finalized") {
//         console.log("[WS] gecko_win_match_finalized", message.data);
//         onGeckoMatchFinalizedRef.current?.({
//           match_key: message.data?.match_key,
//           partner_user_id: message.data?.partner_user_id,
//         });
//         return;
//       }

//       if (message.action === "gecko_win_accepted") {
//         console.log("[WS] gecko_win_accepted", message.data);
//         const deletedCapsuleId = message.data?.deleted_capsule_id ?? null;

//         if (deletedCapsuleId) {
//           onRemoveCapsuleRef.current?.(deletedCapsuleId);
//         }

//         return;
//       }

//       if (message.action === "gecko_win_declined") {
//         console.log("[WS] gecko_win_declined", message.data);
//         return;
//       }

//       if (message.action === "score_state") {
//         const backendEnergyUpdatedAt = message.data?.energy_updated_at ?? null;

//         if (
//           !hasReceivedInitialScoreStateRef.current &&
//           backendEnergyUpdatedAt
//         ) {
//           hasReceivedInitialScoreStateRef.current = true;
//           initialBackendEnergyUpdatedAtRef.current = backendEnergyUpdatedAt;
//         }

//         latestBackendEnergyUpdatedAtRef.current = backendEnergyUpdatedAt;
//         publishScoreState(message.data);
//         return;
//       }

//       if (message.action === "gecko_message") {
//         geckoMessageSV.value = {
//           from_user: message.data?.from_user,
//           message: message.data?.message ?? null,
//           received_at: performance.now(),
//         };

//         onGeckoMessageRef.current?.(message.data);
//         return;
//       }

//       if (message.action === "gecko_coords") {
//         if (
//           Array.isArray(message.data?.position) &&
//           message.data.position.length === 2
//         ) {
//           peerGeckoPositionSV.value = {
//             from_user: message.data.from_user,
//             position: message.data.position,
//             received_at: performance.now(),
//           };

//           onGeckoCoordsRef.current?.(message.data);
//         }

//         return;
//       }

//       if (message.action === "host_gecko_coords") {
//         if (
//           Array.isArray(message.data?.position) &&
//           message.data.position.length === 2
//         ) {
//           hostPeerGeckoPositionSV.value = {
//             from_user: message.data.from_user,
//             position: message.data.position,
//             steps: message.data.steps,
//             first_fingers: message.data.first_fingers,
//             held_moments: message.data.held_moments,
//             held_moments_len: message.data.held_moments_len,
//             moments: message.data.moments,
//             moments_len: message.data.moments_len,
//             received_at: performance.now(),
//           };

//           onHostGeckoCoordsRef.current?.(message.data);
//         }

//         return;
//       }

//       if (message.action === "all_host_capsules") {
//         const moments = message.data?.moments ?? [];
//         const momentsLen = message.data?.moments_len ?? moments.length;

//         hostCapsulesSV.value = {
//           from_user: message.data?.from_user,
//           moments,
//           moments_len: momentsLen,
//           received_at: performance.now(),
//         };

//         return;
//       }

//       if (message.action === "capsule_progress") {
//         console.log("HURRAY! capsule progress update received:", message.data);

//         const capsuleId = message.data?.capsule_id;
//         const newProgress = Number(message.data?.new_progress);

//         if (capsuleId && Number.isFinite(newProgress)) {
//           onCapsuleProgressRef.current?.({
//             capsule_id: capsuleId,
//             new_progress: newProgress,
//             from_user: message.data?.from_user,
//           });
//         }

//         return;
//       }

//       if (message.action === "guest_gecko_coords") {
//         if (
//           Array.isArray(message.data?.position) &&
//           message.data.position.length === 2
//         ) {
//           guestPeerGeckoPositionSV.value = {
//             from_user: message.data.from_user,
//             position: message.data.position,
//             steps: message.data.steps,
//             received_at: performance.now(),
//           };

//           onGuestGeckoCoordsRef.current?.(message.data);
//         }

//         return;
//       }

//       if (message.action === "join_live_sesh_ok") {
//         const partnerId = message.data?.partner_id ?? null;
//         setLiveSeshPartner(
//           partnerId == null
//             ? null
//             : {
//                 userId: partnerId,
//                 username: message.data?.partner_username ?? null,
//                 friendId: message.data?.partner_friend_id ?? null,
//                 friendName: message.data?.partner_friend_name ?? null,
//               },
//         );
//         console.log(`SESSSIONNNNNNNNNN`, message.data);
//         onJoinLiveSeshRef.current?.(partnerId);
//         requestPresenceStatus();
//         return;
//       }
//       if (message.action === "join_live_sesh_failed") {
//         setLiveSeshPartner(null);
//         onJoinLiveSeshRef.current?.(null);
//         return;
//       }

//       if (message.action === "leave_live_sesh_ok") {
//         setLiveSeshPartner(null);
//         onLeaveLiveSeshRef.current?.();
//         return;
//       }

//       if (message.action === "live_sesh_cancelled") {
//         onLiveSeshCancelledRef.current?.(message.data ?? {});
//         return;
//       }

//       // pong / rust_error / unknown — ignored.
//     };

//     ws.onclose = (event) => {
//       socketStatusSV.value = "disconnected";
//       stopFlushInterval();
//       stopPingInterval();

//       isFriendBoundRef.current = false;
//       boundFriendIdRef.current = null;

//       if (shouldReconnectRef.current && wantsConnectionRef.current) {
//         reconnectTimeoutRef.current = setTimeout(() => {
//           connect();
//         }, 3000);
//       }

//       console.log(
//         `[WS] disconnected — code=${event.code} reason=${event.reason}`,
//       );
//     };

//     ws.onerror = (error) => {
//       console.log("[WS] error", error);
//       ws.close();
//     };

//     wsRef.current = ws;
//   }, [
//     clearReconnectTimeout,
//     flushPendingUpdateGeckoData,
//     geckoMessageSV,
//     getGeckoScreenPosition,
//     getScoreState,
//     guestPeerGeckoPositionSV,
//     hostCapsulesSV,
//     hostPeerGeckoPositionSV,
//     joinLiveSesh,
//     matchesSV,
//     peerGeckoPositionSV,
//     peerJoinedStatusSV,
//     sharedColorLightSV,
//     sharedColorDarkSV,
//     publishScoreState,
//     requestPresenceStatus,
//     sendSetFriend,
//     socketStatusSV,
//     startFlushInterval,
//     stopFlushInterval,
//     startPingInterval,
//     stopPingInterval,
//   ]);

//   const setWantsConnection = useCallback(
//     (wants: boolean) => {
//       wantsConnectionRef.current = wants;

//       if (!wants) {
//         disconnect();
//       }
//     },
//     [disconnect],
//   );

//   useEffect(() => {
//     const handleAppStateChange = (state: AppStateStatus) => {
//       if (state === "background" || state === "inactive") {
//         if (wsRef.current) {
//           disconnect();
//         }
//       } else if (state === "active") {
//         if (
//           wantsConnectionRef.current &&
//           wsRef.current?.readyState !== WebSocket.OPEN
//         ) {
//           connect();
//         }
//       }
//     };

//     const sub = AppState.addEventListener("change", handleAppStateChange);
//     return () => sub.remove();
//   }, [connect, disconnect]);

//   const value = useMemo<GeckoWebsocketContextValue>(
//     () => ({
//       socketStatusSV,
//       peerJoinedStatusSV,
//       sharedColorLightSV,
//       sharedColorDarkSV,

//       scoreStateRef,
//       liveSeshPartner,

//       energySV,
//       peerGeckoPositionSV,
//       hostPeerGeckoPositionSV,
//       guestPeerGeckoPositionSV,

//       hasReceivedInitialScoreStateRef,
//       initialBackendEnergyUpdatedAtRef,
//       latestBackendEnergyUpdatedAtRef,
//       multiplierRef,

//       geckoMessageSV,
//       wsRef,

//       connect,
//       disconnect,
//       setWantsConnection,

//       bindFriend,
//       clearFriendBinding,
//       getFriendBindingState,

//       flush,
//       sendRaw,

//       getScoreState,
//       getGeckoScreenPosition,
//       joinLiveSesh,
//       leaveLiveSesh,

//       updateGeckoData,

//       sendGeckoPosition,
//       sendHostGeckoPosition,
//       sendGuestGeckoPosition,

//       registerOnScoreState,
//       registerOnSync,
//       registerOnGeckoCoords,
//       registerOnHostGeckoCoords,
//       registerOnGuestGeckoCoords,
//       registerOnJoinLiveSesh,
//       registerOnLeaveLiveSesh,
//       registerOnLiveSeshCancelled,
//       registerOnGeckoMessage,

//       requestPresenceStatus,
//       sendReadStatusToGecko,
//       sendFETextToGecko,
//       matchesSV,
//       sendMatchRequest,
//       proposeGeckoWin,
//       registerOnGeckoWinProposed,
//       proposeGeckoMatchWin,
//       registerOnGeckoMatchWinNavigate,
//       registerOnGeckoMatchPendingAcceptPartner,
//       registerOnGeckoMatchFinalized,
//       registerOnForceDisconnect,
//       registerOnRemoveCapsule,
//       sendCapsuleProgress,
//       sendAllHostCapsules,
//       hostCapsulesSV,
//       registerOnPeerPresence,
//       registerOnCapsuleProgress,
//       capsuleProgressSV,
//       repullCapsuleMatches,
//     }),
//     [
//       bindFriend,
//       capsuleProgressSV,
//       clearFriendBinding,
//       connect,
//       disconnect,
//       energySV,
//       flush,
//       geckoMessageSV,
//       getFriendBindingState,
//       getGeckoScreenPosition,
//       getScoreState,
//       guestPeerGeckoPositionSV,
//       hostCapsulesSV,
//       hostPeerGeckoPositionSV,
//       joinLiveSesh,
//       leaveLiveSesh,
//       liveSeshPartner,
//       matchesSV,
//       peerGeckoPositionSV,
//       peerJoinedStatusSV,
//       proposeGeckoMatchWin,
//       proposeGeckoWin,
//       registerOnCapsuleProgress,
//       registerOnForceDisconnect,
//       registerOnGeckoCoords,
//       registerOnGeckoMatchFinalized,
//       registerOnGeckoMatchPendingAcceptPartner,
//       registerOnGeckoMatchWinNavigate,
//       registerOnGeckoMessage,
//       registerOnGeckoWinProposed,
//       registerOnGuestGeckoCoords,
//       registerOnHostGeckoCoords,
//       registerOnJoinLiveSesh,
//       registerOnLeaveLiveSesh,
//       registerOnLiveSeshCancelled,
//       registerOnPeerPresence,
//       registerOnRemoveCapsule,
//       registerOnScoreState,
//       registerOnSync,
//       repullCapsuleMatches,
//       requestPresenceStatus,
//       sendAllHostCapsules,
//       sendCapsuleProgress,
//       sendFETextToGecko,
//       sendGeckoPosition,
//       sendGuestGeckoPosition,
//       sendHostGeckoPosition,
//       sendMatchRequest,
//       sendRaw,
//       sendReadStatusToGecko,
//       setWantsConnection,
//       sharedColorDarkSV,
//       sharedColorLightSV,
//       socketStatusSV,
//       updateGeckoData,
//     ],
//   );

//   return (
//     <GeckoWebsocketContext.Provider value={value}>
//       {children}
//     </GeckoWebsocketContext.Provider>
//   );
// };

// export const useGeckoWebsocket = () => {
//   const ctx = useContext(GeckoWebsocketContext);

//   if (!ctx) {
//     throw new Error(
//       "useGeckoWebsocket must be used inside GeckoWebsocketProvider",
//     );
//   }

//   return ctx;
// };
