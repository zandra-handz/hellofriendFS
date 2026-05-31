import React, { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { useFocusEffect } from "@react-navigation/native";
import {
  View,
  StyleSheet,
  Alert,
  AppState,
} from "react-native";
import useCancelCurrentLiveSesh from "@/src/hooks/LiveSeshCalls/useCancelLiveSesh";
import { useGeckoWebsocket } from "@/src/context/GeckoWebsocketContext";
import { useLDTheme } from "@/src/context/LDThemeContext";
import useCurrentLiveSesh from "@/src/hooks/LiveSeshCalls/useCurrentLiveSesh";
import MemoizedMirrorPlayGecko from "@/app/assets/shader_animations/MirrorPlayGecko";
import manualGradientColors from "@/app/styles/StaticColors";
import { showFlashMessage } from "@/src/utils/ShowFlashMessage";
import useUser from "@/src/hooks/useUser";
import GlassPreviewBottomSecret from "./GlassPreviewBottomSecret";
import GlassTopBarLight from "./GlassTopBarLight";
import useAppNavigations from "@/src/hooks/useAppNavigations";
import useGeckoScoreState from "@/src/hooks/useGeckoScoreState";

import SafeViewSecretGecko from "@/app/components/appwide/format/SafeViewSecretGecko";
// optional (only if you added backend broadcast)
// import PeerEnergyText from "@/app/components/debug/PeerEnergyText";

type Props = {
  skiaFontLarge: SkFont;
  skiaFontSmall: SkFont;
};

const ScreenSecretGecko = ({ skiaFontLarge, skiaFontSmall }: Props) => {
  const {
    socketStatusSV,
    peerJoinedStatusSV,
    geckoMessageSV,

    liveSeshPartner,
    // energySV,
    peerGeckoPositionSV,
    guestPeerGeckoPositionSV,
    hostPeerGeckoPositionSV,
    sharedColorLightSV,
    sharedColorDarkSV,

    connect,
    setWantsConnection,
    // joinLiveSesh is no longer called directly here. The guest now confirms
    // it is on this screen first (bindGuestScreen → set_guest_on_screen), and
    // the join is fired from the set_guest_on_screen_ok handler in the context,
    // exactly as the host joins from set_friend_ok.
    leaveLiveSesh,
    bindGuestScreen,
    clearGuestScreen,
    sendGeckoPosition,
    sendGuestGeckoPosition,

    requestPresenceStatus,
    registerOnGeckoWinProposed,
    registerOnGeckoMatchWinNavigate,
    sendCapsuleProgress,
    hostCapsulesSV,
    registerOnPeerPresence,
    seed24hRef,
    registerOnSeed24h,
    myPointsSV,
    partnerPointsSV,
  } = useGeckoWebsocket();

  const { user } = useUser();

  const { lightDarkTheme } = useLDTheme();
  const { geckoScoreState, geckoConfigs } = useGeckoScoreState();

    const colorGeckoBody0 = useMemo(() => {
      if (geckoConfigs?.color_gecko_body_0) {
        return geckoConfigs?.color_gecko_body_0;
      }
      return manualGradientColors.homeDarkColor;
    }, [geckoConfigs?.color_gecko_body_0]);

    const colorGeckoOutline0 = useMemo(() => {
      if (geckoConfigs?.color_gecko_outline_0) {
        return geckoConfigs?.color_gecko_outline_0;
      }
      return manualGradientColors.lightColor;
    }, [geckoConfigs?.color_gecko_outline_0]);

  const textColor = lightDarkTheme.primaryText;
  const darkerOverlayColor = lightDarkTheme.darkerOverlayBackground;
  const darkerGlassColor = lightDarkTheme.darkerGlassBackground;

  const { navigateBack, navigateToSecretGeckoWinAccept } = useAppNavigations();
  const handleExit = React.useCallback(() => {
    leaveLiveSesh();
    navigateBack();
  }, [leaveLiveSesh, navigateBack]);
  const { handleCancelCurrentLiveSesh } = useCancelCurrentLiveSesh({
    userId: user?.id,
  });

  useEffect(() => {
    const wasOnlineRef = { current: false };
    const unsub = registerOnPeerPresence((online) => {
      if (wasOnlineRef.current && !online) {
        showFlashMessage(`You are alone...`, false, 1000);
      }
      wasOnlineRef.current = online;
    });
    return unsub;
  }, [registerOnPeerPresence]);

  const handleCancelPress = React.useCallback(() => {
    Alert.alert(
      "End session?",
      "This will end the session for both you and your partner.",
      [
        { text: "Keep it", style: "cancel" },
        {
          text: "End session",
          style: "destructive",
          onPress: async () => {
            await handleCancelCurrentLiveSesh();
            leaveLiveSesh();
            navigateBack();
          },
        },
      ],
    );
  }, [handleCancelCurrentLiveSesh, leaveLiveSesh, navigateBack]);
  const { isHost, playMode, playModeLabel } = useCurrentLiveSesh({
    userId: user?.id,
    enabled: true,
  });

  const rerenderCountRef = useRef(0);

  rerenderCountRef.current += 1;

  console.log(`ScreenGecko renders: `, rerenderCountRef.current);

  const noopSendGuestGeckoPosition = useRef(() => {}).current;

  const sendCapsuleProgressRef = useRef(
    !isHost ? sendCapsuleProgress : () => {},
  );

  useEffect(() => {
    sendCapsuleProgressRef.current = !isHost ? sendCapsuleProgress : () => {};
  }, [sendCapsuleProgress, isHost]);

  const sendGuestGeckoPositionRef = useRef(
    !isHost ? sendGuestGeckoPosition : noopSendGuestGeckoPosition,
  );
  useEffect(() => {
    sendGuestGeckoPositionRef.current = !isHost
      ? sendGuestGeckoPosition
      : noopSendGuestGeckoPosition;
  }, [sendGuestGeckoPosition, isHost, noopSendGuestGeckoPosition]);

  // useEffect(() => {
  //   // auto join when screen mounts
  //   joinLiveSesh();

  //   return () => {
  //     leaveLiveSesh();
  //   };
  // }, [joinLiveSesh, leaveLiveSesh]);

  useFocusEffect(
    useCallback(() => {
      requestPresenceStatus();
    }, [requestPresenceStatus]),
  );

  useEffect(() => {
    registerOnGeckoMatchWinNavigate((payload) => {
      if (!payload?.pending_id) return;
      navigateToSecretGeckoWinAccept({
        pendingId: payload.pending_id,
        oneDirectional: false,
      });
    });

    registerOnGeckoWinProposed(() => {
      navigateToSecretGeckoWinAccept({ pendingId: null, oneDirectional: true });
    });

    return () => {
      registerOnGeckoMatchWinNavigate(() => {});
      registerOnGeckoWinProposed(() => {});
    };
  }, [
    registerOnGeckoMatchWinNavigate,
    registerOnGeckoWinProposed,
    navigateToSecretGeckoWinAccept,
  ]);

  // useEffect(() => {
  //   const sub = AppState.addEventListener("change", (state) => {
  //     if (state === "active") {

  //         showFlashMessage(`Appstate active, requesting presence status`, false, 1000);
  //       requestPresenceStatus();
  //     }
  //   });
  //   return () => sub.remove();
  // }, [requestPresenceStatus]);

  // NEW THING TO TRY INSTEAD OF APP STATE ABOVE
  // IF ITS STILL HERE I HAVENT TRIED IT YET

  //   const resumePresenceCheck = useCallback(() => {
  //   console.log("[SECRET GECKO] resumePresenceCheck");

  //   setWantsConnection(true);

  //   connect().then(() => {
  //     joinLiveSesh();
  //     requestPresenceStatus();

  //     setTimeout(() => {
  //       requestPresenceStatus();
  //     }, 350);
  //   });
  // }, [
  //   setWantsConnection,
  //   connect,
  //   joinLiveSesh,
  //   requestPresenceStatus,
  // ]);

  // useEffect(() => {
  //   const sub = AppState.addEventListener("change", (state) => {
  //     console.log("[SECRET GECKO] AppState:", state);

  //     if (state === "active") {
  //       resumePresenceCheck();
  //     }
  //   });

  //   return () => sub.remove();
  // }, [resumePresenceCheck]);

  useFocusEffect(
    useCallback(() => {
      let isActive = true;

      const setup = async () => {
        console.log("[SECRET GECKO] focus -> connect");
        setWantsConnection(true);
        await connect();

        if (!isActive) return;

        // Confirm we are on the guest screen BEFORE joining, mirroring how the
        // host calls bindFriend (set_friend) before joining. The join is fired
        // from the set_guest_on_screen_ok handler once the server has marked us
        // present and put us in the partner room. On a fresh connect the
        // confirm is (re)sent from ws.onopen.
        console.log("[SECRET GECKO] focus -> bindGuestScreen");
        bindGuestScreen();
      };

      setup();

      return () => {
        isActive = false;
        console.log(
          "[SECRET GECKO] blur -> leaveLiveSesh + clearGuestScreen + setWantsConnection(false)",
        );
        // leaveLiveSesh tears down server presence (and clears guest_on_screen
        // server-side); clearGuestScreen is the local-only reset, mirroring the
        // host's leaveLiveSesh + clearFriendBinding blur sequence.
        leaveLiveSesh();
        clearGuestScreen();
        setWantsConnection(false);
      };
    }, [
      connect,
      setWantsConnection,
      bindGuestScreen,
      clearGuestScreen,
      leaveLiveSesh,
    ]),
  );

  const [resetSkia, setResetSkia] = useState<number | null>(null);

  useEffect(() => {
    const sub = AppState.addEventListener("change", (s) => {
      if (s === "active") setResetSkia(Date.now());
    });
    return () => sub.remove();
  }, []);

  useEffect(() => {
    const sub = AppState.addEventListener("change", (state) => {
      const socketStatus = socketStatusSV.value;
      const peerJoined = peerJoinedStatusSV.value;
      const hasPartner = !!liveSeshPartner;

      if (state === "active") {
        showFlashMessage(
          `ACTIVE | socket:${socketStatus} | peer:${peerJoined ? "Y" : "N"} | partner:${hasPartner ? "Y" : "N"} | host:${isHost ? "Y" : "N"}`,
          false,
          2500,
        );

        requestPresenceStatus();

        setTimeout(() => {
          showFlashMessage(
            `+350ms | socket:${socketStatusSV.value} | peer:${peerJoinedStatusSV.value ? "Y" : "N"} | partner:${liveSeshPartner ? "Y" : "N"}`,
            false,
            2500,
          );
        }, 350);
      }
    });

    return () => sub.remove();
  }, [
    requestPresenceStatus,
    socketStatusSV,
    peerJoinedStatusSV,
    liveSeshPartner,
    isHost,
  ]);

  return (
    // <GradientBackgroundAppDefault style={styles.backgroundContainer}>
    <SafeViewSecretGecko
      sharedColorLightSV={sharedColorLightSV}
      sharedColorDarkSV={sharedColorDarkSV}
    >
      {/* <View style={{ width: "100%", alignItems: "center", bottom: -50 }}>
        <Text style={styles.label}>socket: {socketStatus}</Text>

        <Text style={styles.label}>partner: {liveSeshPartnerId ?? "—"}</Text>

        <PeerGeckoPositionText
          peerGeckoPositionSV={hostPeerGeckoPositionSV}
          color="white"
        />
      </View> */}

      <View
        style={{
          position: "absolute",
          top: 280,
          left: 12,
          zIndex: 999,
        }}
        pointerEvents="none"
      >
        {/* <PeerGeckoPositionText
          peerGeckoPositionSV={peerGeckoPositionSV}
          color="white"
        />
        <PeerGeckoPositionText
          peerGeckoPositionSV={hostPeerGeckoPositionSV}
          color="white"
        />
        <PeerGeckoPositionText
          peerGeckoPositionSV={guestPeerGeckoPositionSV}
          color="white"
        /> */}
      </View>

      {/* <EnergyText
        energySV={energySV}
        color="white"
      /> */}

      {/*
      <PeerEnergyText
        peerEnergySV={peerEnergySV}
        color="white"
      />
      */}
      <View style={[StyleSheet.absoluteFill]}>
        <MemoizedMirrorPlayGecko
        color1={colorGeckoOutline0}
          color2={colorGeckoBody0}
          bckgColor1={manualGradientColors.lightColor}
          bckgColor2={manualGradientColors.homeLightColor}
          sharedColorLightSV={sharedColorLightSV}
          sharedColorDarkSV={sharedColorDarkSV}
          //   startingCoord0={0.2}
          //   startingCoord1={-1}
          //   restPoint0={0.5}
          //   restPoint1={0.7}
          startingCoord0={0.1}
          startingCoord1={-0.5}
          restPoint0={0.5}
          restPoint1={0.6}
          scale={1}
          gecko_scale={1}
          //   gecko_size={1.6}
          gecko_size={2.7} //{1.7}
          reset={resetSkia}
          hostPeerGeckoPositionSV={hostPeerGeckoPositionSV}
          hostCapsulesSV={hostCapsulesSV}
          sendGuestGeckoPositionRef={sendGuestGeckoPositionRef}
          playMode={playMode}
          sendCapsuleProgressRef={sendCapsuleProgressRef}
          seed24hRef={seed24hRef}
          registerOnSeed24h={registerOnSeed24h}
        />
      </View>

      <GlassTopBarLight
        socketStatusSV={socketStatusSV}
        peerJoinedStatusSV={peerJoinedStatusSV}
        geckoMessageSV={geckoMessageSV}
        myPointsSV={myPointsSV}
        partnerPointsSV={partnerPointsSV}
        hostPeerGeckoPositionSV={guestPeerGeckoPositionSV}
        guestPeerGeckoPositionSV={hostPeerGeckoPositionSV}
        playModeLabel={playModeLabel}
        liveSeshPartner={liveSeshPartner}
        textColor={textColor}
        backgroundColor={darkerOverlayColor}
        requestPresenceStatus={requestPresenceStatus}
        // friendId={selectedFriend.id}
        friendName={"Unknown"}
        highlight={false}
        fontSmall={skiaFontSmall}
      />
      <GlassPreviewBottomSecret
        color={textColor}
        backgroundColor={darkerGlassColor}
        borderColor={"transparent"}
        onPress_exit={handleExit}
        onPress_cancel={handleCancelPress}
      />
      {/* </GradientBackgroundAppDefault> */}
    </SafeViewSecretGecko>
  );
};

export default ScreenSecretGecko;

// const styles = StyleSheet.create({
//   backgroundContainer: {
//     flex: 1,
//     flexDirection: "column",
//     justifyContent: "flex-end",
//   },
//   title: {
//     color: "white",
//     fontSize: 18,
//     marginBottom: 8,
//   },
//   label: {
//     color: "white",
//     fontSize: 13,
//   },
// });
