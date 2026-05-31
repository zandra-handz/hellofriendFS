# GeckoWebsocketContext changes — guest on-screen gate

These mirror the host's `friend_id` flow exactly. The guest never sends a
`friend_id`; instead it confirms `is_on_guest_screen`, and the Rust socket gates
guest presence/room-join on that boolean the same way it gates the host on
`friend_id == sesh_friend_id`.

Apply these 8 surgical edits to `GeckoWebsocketContext.tsx`. Nothing else changes.

---

## 1. Type — add to `GeckoWebsocketContextValue`

Find:

```ts
  clearFriendBinding: () => boolean;
  getFriendBindingState: () => {
```

Insert the two new methods just above `getFriendBindingState`:

```ts
  clearFriendBinding: () => boolean;
  bindGuestScreen: () => boolean;
  clearGuestScreen: () => boolean;
  getFriendBindingState: () => {
```

---

## 2. Refs — add next to the friend-binding refs

Find:

```ts
  const boundFriendIdRef = useRef<number | null>(null);
  const isFriendBoundRef = useRef(false);
```

Insert right after:

```ts
  const boundFriendIdRef = useRef<number | null>(null);
  const isFriendBoundRef = useRef(false);

  // Guest-side analog of the host's friend binding. The guest never sends a
  // friend_id; instead it confirms it is on the sesh (guest) screen. The Rust
  // socket gates guest presence + partner-room membership on this boolean
  // exactly as it gates the host on friend_id == sesh_friend_id.
  // wantsGuestOnScreenRef = intent (set on screen focus, cleared on blur),
  // persists across reconnects so ws.onopen can re-confirm — mirrors
  // pendingFriendIdRef. guestOnScreenConfirmedRef = server ack — mirrors
  // isFriendBoundRef.
  const wantsGuestOnScreenRef = useRef(false);
  const guestOnScreenConfirmedRef = useRef(false);
```

---

## 3. Sender — add right after `sendSetFriend`

Find the end of `sendSetFriend`:

```ts
      return true;
    },
    [],
  );

  const sendRaw = useCallback(
```

Insert `sendSetGuestOnScreen` between `sendSetFriend` and `sendRaw`:

```ts
      return true;
    },
    [],
  );

  // Parallel to sendSetFriend.
  const sendSetGuestOnScreen = useCallback((isOnScreen: boolean) => {
    if (wsRef.current?.readyState !== WebSocket.OPEN) {
      return false;
    }

    wsRef.current.send(
      JSON.stringify({
        action: "set_guest_on_screen",
        data: { is_on_guest_screen: isOnScreen },
      }),
    );

    return true;
  }, []);

  const sendRaw = useCallback(
```

---

## 4. bind/clear — add right after `clearFriendBinding`

Find the end of `clearFriendBinding`:

```ts
    return true;
  }, [guestPeerGeckoPositionSV, hostPeerGeckoPositionSV, peerGeckoPositionSV]);
```

Insert `bindGuestScreen` + `clearGuestScreen` right after it:

```ts
    return true;
  }, [guestPeerGeckoPositionSV, hostPeerGeckoPositionSV, peerGeckoPositionSV]);

  // Parallel to bindFriend: declare intent to be present as a guest and, if the
  // socket is open, confirm on-screen immediately. On a fresh connect the
  // confirm is (re)sent from ws.onopen, mirroring set_friend. The actual join
  // happens on the set_guest_on_screen_ok ack.
  const bindGuestScreen = useCallback(() => {
    wantsGuestOnScreenRef.current = true;
    guestOnScreenConfirmedRef.current = false;

    peerGeckoPositionSV.value = null;
    hostPeerGeckoPositionSV.value = null;
    guestPeerGeckoPositionSV.value = null;

    return sendSetGuestOnScreen(true);
  }, [
    guestPeerGeckoPositionSV,
    hostPeerGeckoPositionSV,
    peerGeckoPositionSV,
    sendSetGuestOnScreen,
  ]);

  // Parallel to clearFriendBinding: LOCAL reset only. Server-side presence is
  // torn down by leaveLiveSesh (which also clears guest_on_screen) / disconnect,
  // exactly as the host relies on leaveLiveSesh while clearFriendBinding is local.
  const clearGuestScreen = useCallback(() => {
    wantsGuestOnScreenRef.current = false;
    guestOnScreenConfirmedRef.current = false;

    peerGeckoPositionSV.value = null;
    hostPeerGeckoPositionSV.value = null;
    guestPeerGeckoPositionSV.value = null;

    return true;
  }, [guestPeerGeckoPositionSV, hostPeerGeckoPositionSV, peerGeckoPositionSV]);
```

---

## 5. ws.onopen — add the guest branch

Find (inside `ws.onopen`):

```ts
      if (fid != null) {
        sendSetFriend(fid, fLightColor, fDarkColor);
        console.log("sending friend");
      } else {
```

Change to:

```ts
      if (fid != null) {
        sendSetFriend(fid, fLightColor, fDarkColor);
        console.log("sending friend");
      } else if (wantsGuestOnScreenRef.current) {
        // Guest path: confirm on-screen before joining, mirroring how the host
        // sends set_friend before join. join fires on set_guest_on_screen_ok.
        sendSetGuestOnScreen(true);
        console.log("sending guest on-screen confirm");
      } else {
```

---

## 6. ws.onmessage — add the ack handlers

Find the `set_friend_failed` handler:

```ts
      if (message.action === "set_friend_failed") {
        console.log("[WS] set_friend_failed", message.data);

        isFriendBoundRef.current = false;
        boundFriendIdRef.current = null;
        return;
      }
```

Insert the two guest handlers right after it:

```ts
      if (message.action === "set_friend_failed") {
        console.log("[WS] set_friend_failed", message.data);

        isFriendBoundRef.current = false;
        boundFriendIdRef.current = null;
        return;
      }

      if (message.action === "set_guest_on_screen_ok") {
        const onScreen = message.data?.is_on_guest_screen ?? false;
        console.log("[WS] set_guest_on_screen_ok", onScreen);

        guestOnScreenConfirmedRef.current = onScreen;

        if (onScreen) {
          // Mirror set_friend_ok: the server now considers us present and has
          // joined us into the partner room, so ask for our position and join
          // the live sesh. The host's peer_presence handler dumps capsules to us.
          getGeckoScreenPosition();
          joinLiveSesh();
        }
        return;
      }

      if (message.action === "set_guest_on_screen_failed") {
        console.log("[WS] set_guest_on_screen_failed", message.data);
        guestOnScreenConfirmedRef.current = false;
        return;
      }
```

---

## 7. disconnect() and onclose — reset the confirmed flag

In `disconnect()`, find:

```ts
    isFriendBoundRef.current = false;
    boundFriendIdRef.current = null;

    setLiveSeshPartner(null);
```

Change to (note: do NOT clear `wantsGuestOnScreenRef` — like `pendingFriendIdRef`
it must survive a reconnect so we re-confirm on the next open):

```ts
    isFriendBoundRef.current = false;
    boundFriendIdRef.current = null;
    guestOnScreenConfirmedRef.current = false;

    setLiveSeshPartner(null);
```

In `ws.onclose`, find:

```ts
      isFriendBoundRef.current = false;
      boundFriendIdRef.current = null;

      if (shouldReconnectRef.current && wantsConnectionRef.current) {
```

Change to:

```ts
      isFriendBoundRef.current = false;
      boundFriendIdRef.current = null;
      guestOnScreenConfirmedRef.current = false;

      if (shouldReconnectRef.current && wantsConnectionRef.current) {
```

---

## 8. Context `value` — expose the two functions

In the `value` useMemo object, find:

```ts
      bindFriend,
      clearFriendBinding,
      getFriendBindingState,
```

Change to:

```ts
      bindFriend,
      clearFriendBinding,
      bindGuestScreen,
      clearGuestScreen,
      getFriendBindingState,
```

And in that same useMemo's dependency array, find:

```ts
      bindFriend,
      capsuleProgressSV,
      clearFriendBinding,
```

Change to:

```ts
      bindFriend,
      bindGuestScreen,
      capsuleProgressSV,
      clearFriendBinding,
      clearGuestScreen,
```

---

That's all for the context. `sendSetGuestOnScreen` is used by `bindGuestScreen`
and `ws.onopen`; `bindGuestScreen` / `clearGuestScreen` are consumed by the guest
screen (see `ScreenSecretGecko.tsx`).
