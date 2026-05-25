import { useEffect, useRef, useCallback, useState } from "react";
import { useSharedValue } from "react-native-reanimated";
import * as SecureStore from "expo-secure-store";
import { getSocketURL, subscribeStagingMode } from "@/app/styles/DevMode";

// FOR DEV ONLY, REMOVE FOR PROD
// Mirrors GeckoWebsocketContext: resolve the host from staging mode and
// refresh it once whenever staging mode is toggled/hydrated. The next
// connect() picks up the new host.
let NOTIFICATIONS_SOCKET_HOST = getSocketURL();
subscribeStagingMode(() => {
  NOTIFICATIONS_SOCKET_HOST = getSocketURL();
});
const NOTIFICATIONS_SOCKET_PATH = "/ws/notifications/";

type InviteData = {
  from_user: number;
  from_username?: string;
  sesh_id?: number | string;
  [k: string]: any;
};

// Payload shape from users/views.py:accept_live_sesh_invite
type InviteAcceptedData = {
  invite_id: number;
  accepted_by: number;
  accepted_by_username: string;
  session_start: string;   // ISO
  expires_at: string;      // ISO
  session_id: string;      // UUID — connects PastMeet to gecko data
  friend_id: number | null;
  hello_id: string | null; // UUID of the newly-created PastMeet
};

type InviteDeclinedData = {
  from_user: number;
  sesh_id?: number | string;
  [k: string]: any;
};

type SeshEndedData = {
  from_user?: number;
  sesh_id?: number | string;
  [k: string]: any;
};

// Fired whenever this user's PastMeets for `friend_id` change (created or
// updated). FE should refetch that friend's hello list. Sent on accept,
// and will be sent from any future mutation site.
type HelloesUpdatedData = {
  friend_id: number;
};

export function useNotificationsSocket() {
  const [socketStatus, setSocketStatus] = useState<
    "connecting" | "connected" | "disconnected"
  >("connecting");

  const socketStatusSV = useSharedValue<
    "connecting" | "connected" | "disconnected"
  >("disconnected");

  const wsRef = useRef<WebSocket | null>(null);
  const reconnectTimeoutRef = useRef<ReturnType<typeof setTimeout> | null>(
    null,
  );
  const pendingActionsRef = useRef<object[]>([]);

  // ----------------------------
  // Event callback refs
  // ----------------------------
  const onInviteRef = useRef<((data: InviteData) => void) | null>(null);
  const onInviteAcceptedRef = useRef<
    ((data: InviteAcceptedData) => void) | null
  >(null);
  const onInviteDeclinedRef = useRef<
    ((data: InviteDeclinedData) => void) | null
  >(null);
  const onSeshEndedRef = useRef<((data: SeshEndedData) => void) | null>(null);
  const onHelloesUpdatedRef = useRef<
    ((data: HelloesUpdatedData) => void) | null
  >(null);
  const onGenericNotificationRef = useRef<((data: any) => void) | null>(null);

  const registerOnLiveSeshInvite = useCallback(
    (cb: (data: InviteData) => void) => {
      onInviteRef.current = cb;
    },
    [],
  );

  const registerOnLiveSeshInviteAccepted = useCallback(
    (cb: (data: InviteAcceptedData) => void) => {
      onInviteAcceptedRef.current = cb;
    },
    [],
  );

  const registerOnLiveSeshInviteDeclined = useCallback(
    (cb: (data: InviteDeclinedData) => void) => {
      onInviteDeclinedRef.current = cb;
    },
    [],
  );

  const registerOnLiveSeshEnded = useCallback(
    (cb: (data: SeshEndedData) => void) => {
      onSeshEndedRef.current = cb;
    },
    [],
  );

  const registerOnHelloesUpdated = useCallback(
    (cb: (data: HelloesUpdatedData) => void) => {
      onHelloesUpdatedRef.current = cb;
    },
    [],
  );

  const registerOnGenericNotification = useCallback(
    (cb: (data: any) => void) => {
      onGenericNotificationRef.current = cb;
    },
    [],
  );

  // ----------------------------
  // Send helpers
  // ----------------------------
  const sendRaw = useCallback((payload: object) => {
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify(payload));
      return true;
    }
    pendingActionsRef.current.push(payload);
    return false;
  }, []);

  const sendLiveSeshInvite = useCallback(
    (toUserId: number, extra: object = {}) => {
      return sendRaw({
        action: "send_live_sesh_invite",
        data: { to_user: toUserId, ...extra },
      });
    },
    [sendRaw],
  );

  const acceptLiveSeshInvite = useCallback(
    (fromUserId: number, seshId?: number | string) => {
      return sendRaw({
        action: "accept_live_sesh_invite",
        data: { from_user: fromUserId, sesh_id: seshId },
      });
    },
    [sendRaw],
  );

  const declineLiveSeshInvite = useCallback(
    (fromUserId: number, seshId?: number | string) => {
      return sendRaw({
        action: "decline_live_sesh_invite",
        data: { from_user: fromUserId, sesh_id: seshId },
      });
    },
    [sendRaw],
  );

  const endLiveSesh = useCallback(
    (seshId?: number | string) => {
      return sendRaw({
        action: "end_live_sesh",
        data: { sesh_id: seshId },
      });
    },
    [sendRaw],
  );

  // ----------------------------
  // Connect / reconnect
  // ----------------------------
  const connect = useCallback(async () => {
    if (reconnectTimeoutRef.current) {
      clearTimeout(reconnectTimeoutRef.current);
      reconnectTimeoutRef.current = null;
    }

    if (wsRef.current) {
      wsRef.current.onclose = null;
      wsRef.current.close();
      wsRef.current = null;
    }

    const token = await SecureStore.getItemAsync("accessToken");
    if (!token) {
      console.log("[NOTIF WS] no access token — skipping connection");
      setSocketStatus("disconnected");
      socketStatusSV.value = "disconnected";
      return;
    }

    setSocketStatus("connecting");
    socketStatusSV.value = "connecting";

    const ws = new WebSocket(
      `${NOTIFICATIONS_SOCKET_HOST}${NOTIFICATIONS_SOCKET_PATH}?token=${token}`,
    );

    ws.onopen = () => {
      console.log("[NOTIF WS] connected");
      setSocketStatus("connected");
      socketStatusSV.value = "connected";

      if (pendingActionsRef.current.length > 0) {
        pendingActionsRef.current.forEach((payload) => {
          ws.send(JSON.stringify(payload));
        });
        pendingActionsRef.current = [];
      }
    };

    ws.onmessage = (event) => {
      let message: any;
      try {
        message = JSON.parse(event.data);
      } catch {
        console.log("[NOTIF WS] failed to parse message");
        return;
      }

      console.log(`[NOTIF WS] <<< ${message.action}`);

      switch (message.action) {
        case "live_sesh_invite":
          onInviteRef.current?.(message.data);
          break;
        case "live_sesh_invite_accepted":
          onInviteAcceptedRef.current?.(message.data);
          break;
        case "live_sesh_invite_declined":
          onInviteDeclinedRef.current?.(message.data);
          break;
        case "live_sesh_ended":
          onSeshEndedRef.current?.(message.data);
          break;
        case "helloes_updated":
          onHelloesUpdatedRef.current?.(message.data);
          break;
        default:
          onGenericNotificationRef.current?.(message);
          break;
      }
    };

    ws.onclose = (event) => {
      console.log(
        `[NOTIF WS] disconnected — code=${event.code} reason=${event.reason}`,
      );
      setSocketStatus("disconnected");
      socketStatusSV.value = "disconnected";

      reconnectTimeoutRef.current = setTimeout(() => {
        connect();
      }, 3000);
    };

    ws.onerror = (error) => {
      console.log("[NOTIF WS] error", error);
      ws.close();
    };

    wsRef.current = ws;
  }, []);

  useEffect(() => {
    console.log("[NOTIF WS] hook mounted");
    connect();

    return () => {
      if (wsRef.current) {
        wsRef.current.onclose = null;
        wsRef.current.close();
        wsRef.current = null;
      }
      if (reconnectTimeoutRef.current) {
        clearTimeout(reconnectTimeoutRef.current);
        reconnectTimeoutRef.current = null;
      }
    };
  }, [connect]);

  return {
    socketStatus,
    socketStatusSV,
    wsRef,
    sendRaw,
    sendLiveSeshInvite,
    acceptLiveSeshInvite,
    declineLiveSeshInvite,
    endLiveSesh,
    registerOnLiveSeshInvite,
    registerOnLiveSeshInviteAccepted,
    registerOnLiveSeshInviteDeclined,
    registerOnLiveSeshEnded,
    registerOnHelloesUpdated,
    registerOnGenericNotification,
  };
}
