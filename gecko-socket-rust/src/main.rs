use axum::{
    extract::{
        ws::{Message, WebSocket, WebSocketUpgrade},
        State,
    },
    http::{HeaderMap, StatusCode},
    response::IntoResponse,
    routing::{get, post},
    Json, Router,
};
use futures_util::{SinkExt, StreamExt};
use serde::{Deserialize, Serialize};
use serde_json::{json, Value};
use std::{
    collections::{HashMap, HashSet},
    net::SocketAddr,
    sync::Arc,
    time::{Duration, Instant, SystemTime, UNIX_EPOCH},
};
use tokio::sync::{mpsc, Notify, RwLock, Semaphore};
use uuid::Uuid;

use jsonwebtoken::{decode, Algorithm, DecodingKey, Validation};
use axum::response::Response;
use tracing::{debug, error, info, warn};
use redis::AsyncCommands;

type UserId = u64;
type ClientId = String;
type RoomName = String;
// type Tx = mpsc::UnboundedSender<Message>;
type Tx = mpsc::Sender<Message>;

/// Per-client coalescing slots for unreliable position frames. Each slot
/// holds at most one pending Message — a newer frame overwrites the older
/// one. The Notify wakes the send_task whenever any slot is populated.
///
/// This prevents head-of-line blocking on the ordered mpsc when the guest's
/// TCP send buffer stalls (mobile network blip, RN backgrounding, etc.).
/// Old positions are pure latency, so we drop them in favor of the newest.
#[derive(Default)]
struct PositionSlots {
    gecko_coords: std::sync::Mutex<Option<Message>>,
    host_gecko_coords: std::sync::Mutex<Option<Message>>,
    guest_gecko_coords: std::sync::Mutex<Option<Message>>,
    notify: Notify,
}

impl PositionSlots {
    /// Route an encoded position frame to its slot. Returns false if the
    /// action isn't a coalescing position kind (caller should fall back to
    /// the ordered mpsc).
    fn put(&self, action: &str, msg: Message) -> bool {
        let slot = match action {
            "gecko_coords" => &self.gecko_coords,
            "host_gecko_coords" => &self.host_gecko_coords,
            "guest_gecko_coords" => &self.guest_gecko_coords,
            _ => return false,
        };
        *slot.lock().unwrap() = Some(msg);
        self.notify.notify_one();
        true
    }

    /// Drain the latest-pending frame from each slot, in a stable order.
    fn drain(&self) -> [Option<Message>; 3] {
        [
            self.gecko_coords.lock().unwrap().take(),
            self.host_gecko_coords.lock().unwrap().take(),
            self.guest_gecko_coords.lock().unwrap().take(),
        ]
    }
}

fn is_coalesced_position_action(action: &str) -> bool {
    matches!(
        action,
        "gecko_coords" | "host_gecko_coords" | "guest_gecko_coords"
    )
}

const PROD_DJANGO_BASE_URL: &str = "https://badrainbowz.com";
const STAGING_DJANGO_BASE_URL: &str = "https://staging.badrainbowz.com";

/// Resolve the Django base URL. Explicit `DJANGO_BASE_URL` wins; otherwise
/// derive from `DJANGO_ENV` (already set per-droplet); default to prod.
fn resolve_django_base_url() -> String {
    if let Ok(url) = std::env::var("DJANGO_BASE_URL") {
        return url;
    }
    match std::env::var("DJANGO_ENV").as_deref() {
        Ok("staging") => STAGING_DJANGO_BASE_URL.to_string(),
        _ => PROD_DJANGO_BASE_URL.to_string(),
    }
}

const BINARY_OUTBOUND_ACTIONS: &[&str] = &[
    "gecko_coords",
    "host_gecko_coords",
    "guest_gecko_coords",
    "all_host_capsules",
    "capsule_progress",
];

#[derive(Clone)]
struct AppState {
    clients: Arc<RwLock<HashMap<ClientId, Client>>>,
    rooms: Arc<RwLock<HashMap<RoomName, Arc<HashSet<ClientId>>>>>,
    http: reqwest::Client,
    internal_secret: String,
    jwt_secret: String,
    django_base_url: String,
    django_concurrency: Arc<Semaphore>,
    redis: redis::aio::ConnectionManager,
}

#[derive(Clone)]
struct Client {
    user_id: UserId,
    tx: Tx,
    position_slots: Arc<PositionSlots>,
    friend_id: Option<u64>,
    is_host: bool,
    // Guest-side analog of the host's friend_id bind. The guest's FE reports
    // whether they're currently on the sesh (guest) screen; presence and room
    // membership are gated on this exactly as the host is gated on
    // friend_id == sesh_friend_id. See sesh_presence_allowed.
    guest_on_screen: bool,
    partner_id: Option<u64>,
    partner_username: Option<String>,
    partner_friend_id: Option<u64>,
    partner_friend_name: Option<String>,
    sesh_friend_id: Option<u64>,
    my_points: u64,
    partner_points: u64,
    // Per-session gecko game win counts, hydrated from Django alongside points
    // and refreshed live via gecko_wins_update pushes.
    my_wins: u64,
    partner_wins: u64,
    own_room: RoomName,
    shared_room: RoomName,
    partner_room: Option<RoomName>,
    friend_light_color: Option<String>,
    friend_dark_color: Option<String>,
    gecko_game_level: Option<u16>,
    gecko_message: Option<String>,
    gecko_emotion: Option<String>,
    gecko_unique_emotion_code: Option<u16>,
    gecko_message_kind: Option<String>,
    gecko_message_ref_id: Option<String>,
    gecko_message_timestamp: Option<i64>,
    // last_seen: Instant,
}

#[derive(Debug, Deserialize)]
 

struct JwtClaims {
    user_id: UserId,
    exp: usize,
}

#[derive(Debug, Serialize)]
struct OutgoingMessage {
    action: String,
    data: Value,
}

#[derive(Debug, Deserialize)]
struct PushUserBody {
    user_id: UserId,
    action: String,
    data: Value,
    #[serde(default)]
    close_after: bool,
}

#[derive(Debug, Deserialize)]
struct PushRoomBody {
    room: String,
    action: String,
    data: Value,
    #[serde(default)]
    exclude_user_id: Option<UserId>,
}

#[derive(Debug, Deserialize)]
struct DisconnectUserBody {
    user_id: UserId,
}


#[repr(u16)]
#[derive(Clone, Copy)]
enum ReadStatus {
    Hi = 1,
    StillReading = 2,
    AllRead = 3, 
}


#[repr(u16)]
#[derive(Clone, Copy)]
enum Filler {
    Hrrm = 999
}



#[repr(u16)]
#[derive(Clone, Copy)]
enum LosingWarning {
    Huh        = 4,
    Digging    = 5,
    Losing     = 6,
    Stolen     = 7,
    FalseAlarm = 8,
}



#[tokio::main]
async fn main() {
    let (nb_writer, _log_guard) = tracing_appender::non_blocking(std::io::stdout());
    tracing_subscriber::fmt()
        .with_env_filter(
            tracing_subscriber::EnvFilter::try_from_default_env()
                .unwrap_or_else(|_| tracing_subscriber::EnvFilter::new("info")),
        )
        .with_writer(nb_writer)
        .with_span_events(tracing_subscriber::fmt::format::FmtSpan::CLOSE)
        .init();

      let redis_url = std::env::var("REDIS_URL")
          .unwrap_or_else(|_| "redis://127.0.0.1:6379/1".to_string());
      let redis_client = redis::Client::open(redis_url)
          .expect("invalid REDIS_URL");
      let redis = redis::aio::ConnectionManager::new(redis_client)
          .await
          .expect("failed to connect to Redis");


    let state = AppState {
        clients: Arc::new(RwLock::new(HashMap::new())),
        rooms: Arc::new(RwLock::new(HashMap::new())),
        http: reqwest::Client::builder()
        .timeout(Duration::from_secs(30))
        .connect_timeout(std::time::Duration::from_secs(5))
        .pool_max_idle_per_host(64)
        .build()
        .expect("failed to build reqwest client"),
        internal_secret: std::env::var("RUST_INTERNAL_SECRET").unwrap_or_default(),
        jwt_secret: std::env::var("GECKO_WS_JWT_SECRET").unwrap_or_default(),
        django_base_url: resolve_django_base_url(),
        django_concurrency: Arc::new(Semaphore::new(10)),
        redis,
    };

    if state.internal_secret.is_empty() {
        warn!("RUST_INTERNAL_SECRET is empty — internal push routes will reject all calls");
    }

    if state.jwt_secret.is_empty() {
        warn!("GECKO_WS_JWT_SECRET is empty — websocket connections will be rejected");
    }

    let app = Router::new()
        .route("/", get(root))
        .route("/ws/gecko-rust-test", get(ws_handler))
        .route("/ws/gecko-rust-test/", get(ws_handler))
        .route("/internal/push/user", post(internal_push_user))
        .route("/internal/push/room", post(internal_push_room))
        .route("/internal/disconnect-user", post(internal_disconnect_user))
        .with_state(state);

    let addr = SocketAddr::from(([127, 0, 0, 1], 4000));
    info!("Rust websocket running at http://{}", addr);

    let listener = tokio::net::TcpListener::bind(addr)
        .await
        .expect("failed to bind Rust websocket server");

    axum::serve(listener, app)
        .await
        .expect("Rust websocket server crashed");
}

async fn root() -> &'static str {
    "rust socket server is running"
}

async fn ws_handler(
    ws: WebSocketUpgrade,
    State(state): State<AppState>,
    headers: HeaderMap,
) -> Response {
    if state.jwt_secret.is_empty() {
        return (StatusCode::INTERNAL_SERVER_ERROR, "socket auth not configured").into_response();
    }

    let proto_header = headers
        .get("sec-websocket-protocol")
        .and_then(|v| v.to_str().ok())
        .unwrap_or("");

    let mut jwt_token: Option<&str> = None;
    for part in proto_header.split(',') {
        let trimmed = part.trim();
        if let Some(rest) = trimmed.strip_prefix("jwt.") {
            jwt_token = Some(rest);
            break;
        }
    }

    let Some(jwt_token) = jwt_token else {
        return (StatusCode::UNAUTHORIZED, "missing jwt subprotocol").into_response();
    };

    let validation = Validation::new(Algorithm::HS256);
    let token_data = match decode::<JwtClaims>(
        jwt_token,
        &DecodingKey::from_secret(state.jwt_secret.as_bytes()),
        &validation,
    ) {
        Ok(d) => d,
        Err(e) => {
            warn!("jwt verify failed: {}", e);
            return (StatusCode::UNAUTHORIZED, "invalid jwt").into_response();
        }
    };

    let user_id = token_data.claims.user_id;

    ws.protocols(["gecko.v1"])
        .on_upgrade(move |socket| handle_socket(socket, user_id, state))
}

async fn handle_socket(socket: WebSocket, user_id: UserId, state: AppState) {
    evict_existing_user(&state, user_id).await;

    let client_id = Uuid::new_v4().to_string();
    let own_room = format!("gecko_energy_{}", user_id);
    let shared_room = format!("gecko_shared_with_friend_{}", user_id);

    let (mut socket_sender, mut socket_receiver) = socket.split();
    // let (tx, mut rx) = mpsc::unbounded_channel::<Message>();
    let (tx, mut rx) = mpsc::channel::<Message>(256);
    let position_slots = Arc::new(PositionSlots::default());

    {
        let mut clients = state.clients.write().await;
        clients.insert(
            client_id.clone(),
            Client {
                user_id,
                tx: tx.clone(),
                position_slots: position_slots.clone(),
                friend_id: None,
                is_host: false,
                guest_on_screen: false,
                partner_id: None,
                partner_username: None,
                partner_friend_id: None,
                partner_friend_name: None,
                sesh_friend_id: None,
                my_points: 0,
                partner_points: 0,
                my_wins: 0,
                partner_wins: 0,
                own_room: own_room.clone(),
                shared_room: shared_room.clone(),
                partner_room: None,
                friend_light_color: None,
                friend_dark_color: None,
                gecko_game_level: None,
                gecko_message: None,
                gecko_emotion: None,
                gecko_unique_emotion_code: None,
                gecko_message_kind: None,
                gecko_message_ref_id: None,
                gecko_message_timestamp: None,
                // last_seen: Instant::now(),
            },
        );
    }

    join_room(&state, &own_room, &client_id).await;
    join_room(&state, &shared_room, &client_id).await;

    send_outgoing(
        &tx,
        OutgoingMessage {
            action: "rust_connected".to_string(),
            data: json!({
                "user_id": user_id,
                "client_id": client_id,
                "own_room": own_room,
                "shared_room": shared_room,
            }),
        },
    );

    {
        let bg_state = state.clone();
        let bg_client_id = client_id.clone();
        tokio::spawn(async move {
            hydrate_live_sesh_context(&bg_state, &bg_client_id).await;

            let Some(client) = get_client(&bg_state, &bg_client_id).await else { return };
            
            let Some(partner_id) = client.partner_id else { return };

            let partner_snapshot = {
                let clients = bg_state.clients.read().await;
                clients
                    .values()
                    .find(|c| c.user_id == partner_id)
                    .filter(|c| sesh_presence_allowed(c))
                    .map(|c| (c.user_id, c.friend_light_color.clone(), c.friend_dark_color.clone(), c.gecko_game_level))
            };

            // Gate initial presence on host bind state. Hosts must confirm
            // via set_friend before we tell either side they're "online and
            // in the sesh." For guests this is always true.
            if sesh_presence_allowed(&client) {
                if let Some((pid, light, dark, level)) = partner_snapshot {
                    send_to_client(
                        &bg_state,
                        &bg_client_id,
                        OutgoingMessage {
                            action: "peer_presence".to_string(),
                            data: json!({
                                "user_id": pid,
                                "online": true,
                                "friend_light_color": light,
                                "friend_dark_color": dark,
                                "gecko_game_level": level,
                            }),
                        },
                    )
                    .await;
                }

                broadcast_peer_presence_online_to_room(
                    &bg_state,
                    &client.shared_room,
                    Some(client.user_id),
                    OutgoingMessage {
                        action: "peer_presence".to_string(),
                        data: json!({
                            "user_id": client.user_id,
                            "online": true,
                            "friend_light_color": client.friend_light_color,
                            "friend_dark_color": client.friend_dark_color,
                            "gecko_game_level": client.gecko_game_level,
                        }),
                    },
                )
                .await;
            }

            if !client.is_host {
                // New guest just landed (initial connect or reconnect). The host's
                // FE design is "full moment dump once on connect, deltas via
                // position frames after" — so the host needs an explicit signal
                // to re-send the full dump. FE responds by firing
                // send_all_host_capsules. broadcast_to_room with exclude_self
                // delivers this to the host (the only other peer in the room).
                broadcast_to_room(
                    &bg_state,
                    &client.shared_room,
                    Some(client.user_id),
                    OutgoingMessage {
                        action: "partner_reconnected".to_string(),
                        data: json!({
                            "user_id": client.user_id,
                        }),
                    },
                )
                .await;

                proxy_check_host_link_and_load(&bg_state, &bg_client_id, partner_id).await;
            }
        });
    }

    let send_task = {
        let position_slots = position_slots.clone();
        tokio::spawn(async move {
            // Select between the ordered event queue and the coalescing
            // position slots. Position frames bypass the mpsc entirely:
            // newer position overwrites older, so a TCP-stall burst at most
            // sends 3 frames (one per kind) instead of N queued positions.
            loop {
                tokio::select! {
                    biased;
                    maybe_msg = rx.recv() => {
                        let Some(message) = maybe_msg else { break };
                        // Flush any pending position frames first so we
                        // don't sit on stale coords while ordered events
                        // pass through.
                        for slot in position_slots.drain() {
                            if let Some(pos) = slot {
                                if socket_sender.send(pos).await.is_err() {
                                    return;
                                }
                            }
                        }
                        let is_close = matches!(message, Message::Close(_));
                        if socket_sender.send(message).await.is_err() {
                            break;
                        }
                        if is_close {
                            break;
                        }
                    }
                    _ = position_slots.notify.notified() => {
                        for slot in position_slots.drain() {
                            if let Some(pos) = slot {
                                if socket_sender.send(pos).await.is_err() {
                                    return;
                                }
                            }
                        }
                    }
                }
            }
        })
    };

    let recv_state = state.clone();
    let recv_client_id = client_id.clone();

    let recv_task = tokio::spawn(async move {
        while let Some(result) = socket_receiver.next().await {
            match result {
                Ok(Message::Text(text)) => {
                    // mark_seen(&recv_state, &recv_client_id).await;
                    match serde_json::from_str::<Value>(&text) {
                        Ok(value) => handle_incoming(&recv_state, &recv_client_id, value).await,
                        Err(_) => {
                            send_to_client(
                                &recv_state,
                                &recv_client_id,
                                OutgoingMessage {
                                    action: "rust_error".to_string(),
                                    data: json!({
                                        "reason": "invalid_json",
                                        "raw": text.to_string(),
                                    }),
                                },
                            )
                            .await;
                        }
                    }
                }
                Ok(Message::Binary(bytes)) => {
                    // mark_seen(&recv_state, &recv_client_id).await;
                    match rmp_serde::from_slice::<Value>(&bytes) {
                        Ok(value) => handle_incoming(&recv_state, &recv_client_id, value).await,
                        Err(_) => {
                            send_to_client(
                                &recv_state,
                                &recv_client_id,
                                OutgoingMessage {
                                    action: "rust_error".to_string(),
                                    data: json!({
                                        "reason": "invalid_msgpack",
                                        "bytes_len": bytes.len(),
                                    }),
                                },
                            )
                            .await;
                        }
                    }
                }
                Ok(Message::Ping(_)) | Ok(Message::Pong(_)) => {}    
                // Ok(Message::Ping(_)) | Ok(Message::Pong(_)) => {
                //     // mark_seen(&recv_state, &recv_client_id).await;
                // }
                Ok(Message::Close(_)) => break,
                Err(err) => {
                    warn!("websocket error client_id={} err={}", recv_client_id, err);
                    break;
                }
            }
        }
    });

    tokio::select! {
        _ = send_task => {},
        _ = recv_task => {},
    }

    disconnect_cleanup(&state, &client_id).await;
}

async fn handle_incoming(state: &AppState, client_id: &str, value: Value) {
    let action = value
        .get("action")
        .and_then(|v| v.as_str())
        .unwrap_or("")
        .to_string();

    let data = value.get("data").cloned();

    match action.as_str() {
        "ping" => {
            send_to_client(
                state,
                client_id,
                OutgoingMessage {
                    action: "pong".to_string(),
                    data: json!({}),
                },
            )
            .await;
        }

        "set_friend" => handle_set_friend(state, client_id, data).await,
        "set_guest_on_screen" => handle_set_guest_on_screen(state, client_id, data).await,
        "join_live_sesh" => handle_join_live_sesh(state, client_id).await,
        "leave_live_sesh" => handle_leave_live_sesh(state, client_id).await,
        "request_peer_presence" => handle_request_peer_presence(state, client_id).await,
        "request_level_change" => handle_request_level_change(state, client_id, data).await,

        "get_gecko_message" => handle_get_gecko_message(state, client_id).await,
        "send_front_end_text_to_gecko" => {
            handle_send_front_end_text_to_gecko(state, client_id, data).await
        }
        "send_read_status_to_gecko" => {
            handle_send_read_status_to_gecko(state, client_id, data).await
        }
        "send_losing_warning_to_gecko" => {
            handle_send_losing_warning_to_gecko(state, client_id, data).await
        }

        "get_gecko_screen_position" => handle_get_gecko_screen_position(state, client_id).await,
        "update_gecko_position" => handle_update_gecko_position(state, client_id, data).await,
        "update_host_gecko_position" => {
            handle_update_host_gecko_position(state, client_id, data).await
        }
        "update_guest_gecko_position" => {
            handle_update_guest_gecko_position(state, client_id, data).await
        }
        "update_capsule_progress" => {
            handle_update_capsule_progress(state, client_id, data).await
        }
        "send_all_host_capsules" => {
            handle_send_all_host_capsules(state, client_id, data).await
        }
        // not in use yet
        "request_all_host_capsules" => {
            handle_request_all_host_capsules(state, client_id).await
        }

        "request_points" => {
            // Spawned so the Django round-trip never stalls this client's
            // message loop (mirrors handle_join_live_sesh).
            let st = state.clone();
            let cid = client_id.to_string();
            tokio::spawn(async move {
                handle_request_points(&st, &cid, data).await;
            });
        }

        "get_24h_seed" => {
            handle_get_24h_seed(state, client_id).await;
        }

        // "get_gecko_wins" => {
        //     handle_get_gecko_wins(state, client_id).await;
        // }

        "get_score_state"
        | "update_gecko_data"
        | "flush"
        | "request_capsule_matches"
        | "repull_capsule_matches"
        | "send_match_request"
        | "propose_gecko_win"
        | "propose_gecko_match_win"
        | "send_validate_win_request"
        | "send_validate_match_win_request" => {
            proxy_action_to_django(state, client_id, &action, data).await;
        }

        _ => {
            send_to_client(
                state,
                client_id,
                OutgoingMessage {
                    action: "rust_error".to_string(),
                    data: json!({
                        "reason": "unknown_action",
                        "action": action,
                    }),
                },
            )
            .await;
        }
    }
}

async fn handle_set_friend(state: &AppState, client_id: &str, data: Option<Value>) {
    let payload = data.unwrap_or_else(|| json!({}));
    let friend_id = payload.get("friend_id").and_then(|v| v.as_u64());

    let Some(friend_id) = friend_id else {
        send_to_client(
            state,
            client_id,
            OutgoingMessage {
                action: "set_friend_failed".to_string(),
                data: json!({ "reason": "invalid_friend_id" }),
            },
        )
        .await;
        return;
    };

    let client_snap = get_client(state, client_id).await;
    if let Some(c) = &client_snap {
        if c.is_host {
            if let Some(sfid) = c.sesh_friend_id {
                if sfid != friend_id {
                    // Host is on a non-matching friend's screen. Reject the
                    // bind AND clear any stale presence frames already sent:
                    // tell this client the partner is offline, and tell the
                    // partner this client is offline (in case prior hydrate
                    // or join_live_sesh already painted them online).
                    if let Some(pid) = c.partner_id {
                        send_to_client(
                            state,
                            client_id,
                            OutgoingMessage {
                                action: "peer_presence".to_string(),
                                data: json!({
                                    "user_id": pid,
                                    "online": false,
                                }),
                            },
                        )
                        .await;
                    }
                    broadcast_to_room(
                        state,
                        &c.shared_room,
                        Some(c.user_id),
                        OutgoingMessage {
                            action: "peer_presence".to_string(),
                            data: json!({
                                "user_id": c.user_id,
                                "online": false,
                                "friend_light_color": null,
                                "friend_dark_color": null,
                                "gecko_game_level": null,
                            }),
                        },
                    )
                    .await;

                    // Mismatched host must not remain bound to the shared room.
                    // If a prior matching bind had joined them into the
                    // partner's room, pull them back out now.
                    if let Some(room) = &c.partner_room {
                        leave_room(state, room, client_id).await;
                    }

                    send_to_client(
                        state,
                        client_id,
                        OutgoingMessage {
                            action: "set_friend_failed".to_string(),
                            data: json!({ "reason": "sesh_friend_mismatch" }),
                        },
                    )
                    .await;
                    return;
                }
            }
        }
    }

    {
        let mut clients = state.clients.write().await;
        if let Some(client) = clients.get_mut(client_id) {
            client.friend_id = Some(friend_id);
            client.friend_light_color = payload
                .get("friend_light_color")
                .and_then(|v| v.as_str())
                .map(|s| s.to_string());
            client.friend_dark_color = payload
                .get("friend_dark_color")
                .and_then(|v| v.as_str())
                .map(|s| s.to_string());
        }
    }

    // A successful bind means the host's FE friend matches the sesh, so bind
    // them into the partner's shared room now — this is the only path that
    // joins a host into that room, so a mismatched host (rejected above) never
    // connects to or receives frames in it. Guests join during hydrate.
    if let Some(c) = get_client(state, client_id).await {
        if sesh_presence_allowed(&c) {
            if let Some(room) = &c.partner_room {
                join_room(state, room, client_id).await;
            }
        }
    }

    send_to_client(
        state,
        client_id,
        OutgoingMessage {
            action: "set_friend_ok".to_string(),
            data: json!({ "friend_id": friend_id }),
        },
    )
    .await;
}

/// Guest-side analog of handle_set_friend. The guest never sends a friend_id —
/// they only ever have one accepted sesh, so "am I looking at it" is a boolean.
/// `true` mirrors the host's matching-friend case (bind into the partner room);
/// `false` mirrors the host's wrong-friend case (clear stale presence on both
/// sides, leave the partner room). No Django round-trips happen here.
async fn handle_set_guest_on_screen(state: &AppState, client_id: &str, data: Option<Value>) {
    let payload = data.unwrap_or_else(|| json!({}));
    let Some(is_on_screen) = payload.get("is_on_guest_screen").and_then(|v| v.as_bool()) else {
        send_to_client(
            state,
            client_id,
            OutgoingMessage {
                action: "set_guest_on_screen_failed".to_string(),
                data: json!({ "reason": "invalid_payload" }),
            },
        )
        .await;
        return;
    };

    // The on-screen boolean is the guest-side bind. A host's screen state is
    // tracked through friend_id (set_friend), so reject this action for hosts
    // rather than silently mutating their state.
    if let Some(c) = get_client(state, client_id).await {
        if c.is_host {
            send_to_client(
                state,
                client_id,
                OutgoingMessage {
                    action: "set_guest_on_screen_failed".to_string(),
                    data: json!({ "reason": "not_a_guest" }),
                },
            )
            .await;
            return;
        }
    }

    {
        let mut clients = state.clients.write().await;
        if let Some(client) = clients.get_mut(client_id) {
            client.guest_on_screen = is_on_screen;
        }
    }

    if !is_on_screen {
        // Guest navigated off their sesh screen. Mirror the host's wrong-friend
        // path: clear any presence we painted on either side and pull the guest
        // out of the partner's shared room so no frames flow to or from them.
        if let Some(c) = get_client(state, client_id).await {
            if let Some(pid) = c.partner_id {
                send_to_client(
                    state,
                    client_id,
                    OutgoingMessage {
                        action: "peer_presence".to_string(),
                        data: json!({
                            "user_id": pid,
                            "online": false,
                        }),
                    },
                )
                .await;
            }
            broadcast_to_room(
                state,
                &c.shared_room,
                Some(c.user_id),
                OutgoingMessage {
                    action: "peer_presence".to_string(),
                    data: json!({
                        "user_id": c.user_id,
                        "online": false,
                        "friend_light_color": null,
                        "friend_dark_color": null,
                        "gecko_game_level": null,
                    }),
                },
            )
            .await;

            if let Some(room) = &c.partner_room {
                leave_room(state, room, client_id).await;
            }
        }

        send_to_client(
            state,
            client_id,
            OutgoingMessage {
                action: "set_guest_on_screen_ok".to_string(),
                data: json!({ "is_on_guest_screen": false }),
            },
        )
        .await;
        return;
    }

    // On-screen: bind the guest into the partner's shared room. This is the
    // only path that joins a guest into that room, so an off-screen guest never
    // receives or emits sesh frames — mirroring the successful set_friend join.
    if let Some(c) = get_client(state, client_id).await {
        if sesh_presence_allowed(&c) {
            if let Some(room) = &c.partner_room {
                join_room(state, room, client_id).await;
            }
        }
    }

    send_to_client(
        state,
        client_id,
        OutgoingMessage {
            action: "set_guest_on_screen_ok".to_string(),
            data: json!({ "is_on_guest_screen": true }),
        },
    )
    .await;
}

async fn handle_join_live_sesh(state: &AppState, client_id: &str) {
    let bg_state = state.clone();
    let bg_client_id = client_id.to_string();
    tokio::spawn(async move {
        let needs_hydrate = {
            let clients = bg_state.clients.read().await;
            clients.get(&bg_client_id).and_then(|c| c.partner_id).is_none()
        };
        if needs_hydrate {
            hydrate_live_sesh_context(&bg_state, &bg_client_id).await;
        }

        let client = get_client(&bg_state, &bg_client_id).await;
        let Some(client) = client else { return };

        debug!(
            target: "peer_pres",
            "join_live_sesh user={} partner_id={:?} shared_room={} partner_room={:?}",
            client.user_id, client.partner_id, client.shared_room, client.partner_room
        );

        let Some(partner_id) = client.partner_id else {
            send_to_client(
                &bg_state,
                &bg_client_id,
                OutgoingMessage {
                    action: "join_live_sesh_failed".to_string(),
                    data: json!({ "reason": "no_active_sesh" }),
                },
            )
            .await;
            return;
        };

        send_to_client(
            &bg_state,
            &bg_client_id,
            OutgoingMessage {
                action: "join_live_sesh_ok".to_string(),
                data: json!({
                    "partner_id": partner_id,
                    "partner_username": client.partner_username,
                    "partner_friend_id": client.partner_friend_id,
                    "partner_friend_name": client.partner_friend_name,
                    "my_points": client.my_points,
                    "partner_points": client.partner_points,
                    "my_wins": client.my_wins,
                    "partner_wins": client.partner_wins,
                }),
            },
        )
        .await;

        if sesh_presence_allowed(&client) {
            broadcast_peer_presence_online_to_room(
                &bg_state,
                &client.shared_room,
                Some(client.user_id),
                OutgoingMessage {
                    action: "peer_presence".to_string(),
                    data: json!({
                        "user_id": client.user_id,
                        "online": true,
                        "friend_light_color": client.friend_light_color,
                        "friend_dark_color": client.friend_dark_color,
                        "gecko_game_level": client.gecko_game_level,
                    }),
                },
            )
            .await;
        }

        if !client.is_host {
            proxy_check_host_link_and_load(&bg_state, &bg_client_id, partner_id).await;
        }
    });
}

async fn handle_leave_live_sesh(state: &AppState, client_id: &str) {
    let client = get_client(state, client_id).await;
    let Some(client) = client else { return };

    debug!(
        target: "peer_pres",
        "leave_live_sesh user={} shared_room={} partner_room={:?}",
        client.user_id, client.shared_room, client.partner_room
    );

    broadcast_to_room(
        state,
        &client.shared_room,
        Some(client.user_id),
        OutgoingMessage {
            action: "peer_presence".to_string(),
            data: json!({
                "user_id": client.user_id,
                "online": false,
                "friend_light_color": null,
                "friend_dark_color": null,
                "gecko_game_level": null,
            }),
        },
    )
    .await;

    if client.is_host {
        broadcast_to_room(
            state,
            &client.shared_room,
            Some(client.user_id),
            OutgoingMessage {
                action: "host_gecko_coords".to_string(),
                data: json!({
                    "from_user": client.user_id,
                    "friend_id": client.friend_id,
                    "position": [0, 0],
                    "steps": [],
                    "steps_len": 0,
                    "first_fingers": [],
                    "held_moments": [],
                    "held_moments_len": 0,
                    "moments": [],
                    "moments_len": 0,
                    "energy": 0.0,
                    "timestamp": null,
                }),
            },
        )
        .await;
    } else {
        broadcast_to_room(
            state,
            &client.shared_room,
            Some(client.user_id),
            OutgoingMessage {
                action: "guest_gecko_coords".to_string(),
                data: json!({
                    "from_user": client.user_id,
                    "position": [0, 0],
                    "steps": [],
                    "energy": 0.0,
                    "timestamp": null,
                }),
            },
        )
        .await;
    }

    if let Some(partner_room) = client.partner_room {
        leave_room(state, &partner_room, client_id).await;
    }

    {
        let mut clients = state.clients.write().await;
        if let Some(c) = clients.get_mut(client_id) {
            c.partner_room = None;
            c.is_host = false;
            c.guest_on_screen = false;
        }
    }

    send_to_client(
        state,
        client_id,
        OutgoingMessage {
            action: "leave_live_sesh_ok".to_string(),
            data: json!({}),
        },
    )
    .await;
}

 
async fn handle_request_peer_presence(state: &AppState, client_id: &str) {                                                                                                                                                                                  
    let client = get_client(state, client_id).await;                                                                                                                                                                                                      
    let Some(client) = client else { return };

    debug!(
        target: "peer_pres",
        "request_peer_presence user={} partner_id={:?}",
        client.user_id, client.partner_id
    );

    let Some(partner_id) = client.partner_id else {
        send_to_client(
            state,
            client_id,
            OutgoingMessage {
                action: "peer_presence".to_string(),
                data: json!({ "online": false }),
            },
        )
        .await;
        return;
    };

    // Host on a non-matching friend screen — pretend partner is offline so
    // the UI doesn't paint sesh state onto the wrong friend.
    if !sesh_presence_allowed(&client) {
        send_to_client(
            state,
            client_id,
            OutgoingMessage {
                action: "peer_presence".to_string(),
                data: json!({
                    "user_id": partner_id,
                    "online": false,
                }),
            },
        )
        .await;
        return;
    }

    let partner = {
        let clients = state.clients.read().await;
        clients
            .values()
            .find(|c| c.user_id == partner_id)
            .cloned()
    };

    if let Some(partner) = partner {
        // Partner is connected, but if THEY're a host whose FE-bound friend
        // doesn't match their sesh (they're on a different friend's screen),
        // we should report them offline so this side doesn't paint them as
        // "in the sesh" when they aren't.
        if !sesh_presence_allowed(&partner) {
            debug!(
                target: "peer_pres",
                "partner={} connected but presence-gated (host on wrong friend), replying offline to user={}",
                partner_id, client.user_id
            );

            send_to_client(
                state,
                client_id,
                OutgoingMessage {
                    action: "peer_presence".to_string(),
                    data: json!({
                        "user_id": partner_id,
                        "online": false,
                    }),
                },
            )
            .await;
            return;
        }

        debug!(
            target: "peer_pres",
            "replying online for partner={} to user={}",
            partner_id, client.user_id
        );

        send_to_client(
            state,
            client_id,
            OutgoingMessage {
                action: "peer_presence".to_string(),
                data: json!({
                    "user_id": partner.user_id,
                    "online": true,
                    "friend_light_color": partner.friend_light_color,
                    "friend_dark_color": partner.friend_dark_color,
                    "gecko_game_level": partner.gecko_game_level,
                }),
            },
        )
        .await;
    } else {
        debug!(
            target: "peer_pres",
            "partner={} not connected, replying offline to user={}",
            partner_id, client.user_id
        );

        send_to_client(
            state,
            client_id,
            OutgoingMessage {
                action: "peer_presence".to_string(),
                data: json!({
                    "user_id": partner_id,
                    "online": false,
                }),
            },
        )
        .await;
    }
}

/// A host or guest changes the shared gecko game level mid-sesh. The level is
/// live shared state (like positions/emotions), so Rust broadcasts the new
/// value to the shared room immediately — both peers apply it with zero Django
/// round-trip — and persists it to the DB in a spawned task so the change
/// survives reconnect/rehydrate. Persistence never blocks this client's loop.
async fn handle_request_level_change(state: &AppState, client_id: &str, data: Option<Value>) {
    let payload = data.unwrap_or_else(|| json!({}));

    // Valid levels mirror Django's GeckoGameLevel choices (1, 2).
    let new_level = match payload.get("new_level").and_then(|v| v.as_u64()) {
        Some(l @ (1 | 2)) => l as u16,
        _ => {
            send_to_client(
                state,
                client_id,
                OutgoingMessage {
                    action: "request_level_change_failed".to_string(),
                    data: json!({ "reason": "invalid_level" }),
                },
            )
            .await;
            return;
        }
    };

    let Some(client) = get_client(state, client_id).await else { return };

    // Only an in-sesh participant (on-screen guest / matching-friend host) may
    // change the level.
    if !sesh_presence_allowed(&client) {
        send_to_client(
            state,
            client_id,
            OutgoingMessage {
                action: "request_level_change_failed".to_string(),
                data: json!({ "reason": "not_in_sesh" }),
            },
        )
        .await;
        return;
    }

    let user_id = client.user_id;
    let shared_room = client.shared_room.clone();
    let partner_id = client.partner_id;

    // Keep Rust's in-memory level fresh for BOTH connected peers so subsequent
    // peer_presence frames report the new level (hydrate only refreshes it on
    // reconnect).
    {
        let mut clients = state.clients.write().await;
        for c in clients.values_mut() {
            if c.user_id == user_id || Some(c.user_id) == partner_id {
                c.gecko_game_level = Some(new_level);
            }
        }
    }

    // Broadcast to the shared room with no exclusion: requester and partner
    // both apply the authoritative new level. New event type so the FE attaches
    // a dedicated listener rather than overloading an existing one.
    broadcast_to_room(
        state,
        &shared_room,
        None,
        OutgoingMessage {
            action: "level_update".to_string(),
            data: json!({
                "gecko_game_level": new_level,
                "changed_by": user_id,
            }),
        },
    )
    .await;

    // Persist to Django (both CurrentLiveSesh rows + cache invalidation) off the
    // hot path so the message loop is never blocked on the round-trip.
    let st = state.clone();
    let cid = client_id.to_string();
    tokio::spawn(async move {
        persist_level_change_to_django(&st, &cid, new_level).await;
    });
}

/// Fire-and-forget DB persistence for a level change. The FE has already been
/// updated via the live broadcast, so we discard the Django response and only
/// log failures — a dropped persist self-heals on the next successful change or
/// is corrected by hydrate from the still-authoritative DB row.
async fn persist_level_change_to_django(state: &AppState, client_id: &str, new_level: u16) {
    let Some(client) = get_client(state, client_id).await else { return };

    let body = json!({
        "user_id": client.user_id,
        "action": "request_level_change",
        "data": { "new_level": new_level },
    });

    let body_bytes = match rmp_serde::to_vec_named(&body) {
        Ok(b) => b,
        Err(err) => {
            error!("persist_level_change: msgpack encode failed err={}", err);
            return;
        }
    };

    let url = format!("{}/users/internal/gecko/socket-action/", state.django_base_url);
    let _permit = state.django_concurrency.acquire().await.ok();
    let response = state
        .http
        .post(url)
        .header("X-Rust-Internal-Secret", &state.internal_secret)
        .header("Content-Type", "application/msgpack")
        .header("Accept", "application/msgpack")
        .body(body_bytes)
        .send()
        .await;

    if let Err(err) = response {
        warn!(
            "persist_level_change: django persist failed user={} err={}",
            client.user_id, err
        );
    }
}

async fn handle_get_gecko_message(state: &AppState, client_id: &str) {
    let client = get_client(state, client_id).await;
    let Some(client) = client else { return };

    send_to_client(
        state,
        client_id,
        OutgoingMessage {
            action: "gecko_message".to_string(),
            data: json!({
                "from_user": client.user_id,
                "message": client.gecko_message,
                "emotion": client.gecko_emotion,
                "unique_emotion_code": client.gecko_unique_emotion_code,
                "kind": client.gecko_message_kind,
                "ref_id": client.gecko_message_ref_id,
                "timestamp": client.gecko_message_timestamp,
            }),
        },
    )
    .await;
}

async fn handle_send_front_end_text_to_gecko(
    state: &AppState,
    client_id: &str,
    data: Option<Value>,
) {
    let payload = data.unwrap_or_else(|| json!({}));
    let message = payload
        .get("message")
        .and_then(|v| v.as_str())
        .map(|s| s.to_string());
    let emotion = payload
        .get("emotion")
        .and_then(|v| v.as_str())
        .map(|s| s.to_string());
    let unique_emotion_code = payload
        .get("unique_emotion_code")
        .and_then(|v| v.as_u64())
        .map(|n| n as u16);
    let kind = payload
        .get("kind")
        .and_then(|v| v.as_str())
        .map(|s| s.to_string());
    let ref_id = payload
        .get("ref_id")
        .and_then(|v| v.as_str())
        .map(|s| s.to_string());
    let timestamp = SystemTime::now()
        .duration_since(UNIX_EPOCH)
        .map(|d| d.as_millis() as i64)
        .ok();

    {
        let mut clients = state.clients.write().await;
        if let Some(client) = clients.get_mut(client_id) {
            client.gecko_message = message.clone();
            client.gecko_emotion = emotion.clone();
            client.gecko_unique_emotion_code = unique_emotion_code.clone();
            client.gecko_message_kind = kind.clone();
            client.gecko_message_ref_id = ref_id.clone();
            client.gecko_message_timestamp = timestamp;
        }
    }

    let client = get_client(state, client_id).await;
    let Some(client) = client else { return };

    send_to_client(
        state,
        client_id,
        OutgoingMessage {
            action: "gecko_message".to_string(),
            data: json!({
                "from_user": client.user_id,
                "message": message,
                "emotion": emotion,
                "unique_emotion_code": unique_emotion_code,
                "kind": kind,
                "ref_id": ref_id,
                "timestamp": timestamp,
            }),
        },
    )
    .await;

    // Share only the gecko's emotion (not the message text) with the partner,
    // using the same shared-room broadcast pattern as positions/presence. The
    // message stays private to the sender; the emotion lets the partner mirror
    // the gecko's mood. New push gets its own event_type so the FE adds a
    // dedicated listener rather than overloading the gecko_message handler.
    broadcast_to_room(
        state,
        &client.shared_room,
        Some(client.user_id),
        OutgoingMessage {
            action: "peer_gecko_emotion".to_string(),
            data: json!({
                "from_user": client.user_id,
                "emotion": client.gecko_emotion,
                "unique_emotion_code": client.gecko_unique_emotion_code,
                "timestamp": timestamp,
            }),
        },
    )
    .await;
}


async fn handle_send_losing_warning_to_gecko(
    state: &AppState,
    client_id: &str,
    data: Option<Value>,
) {
    let payload = data.unwrap_or_else(|| json!({}));
    let code = payload.get("message_code").and_then(|v| v.as_i64());
    let kind = payload.get("kind").cloned();
    let ref_id = payload.get("ref_id").cloned();

    // `message_code` is the FE-sent trigger and its handling is unchanged.
    // `unique_emotion_code` is a separate, globally-unique emotion code we emit,
    // sourced from the LosingWarning enum (Filler::Hrrm is the fallback).
    let (message, emotion, unique_emotion_code) = match code {
        Some(0) => ("Huh? What was that??", "confused", LosingWarning::Huh as u16),
        Some(1) => (
            "They're digging up one of our moments! Gotta do something!",
            "alarmed",
            LosingWarning::Digging as u16,
        ),
        Some(2) => (
            "My man we are losin' the fight here!! They're gonna be able to read it!",
            "panic",
            LosingWarning::Losing as u16,
        ),
        Some(3) => ("MOMENT STOLEN!", "devastated", LosingWarning::Stolen as u16),
        Some(4) => (
            "Whew! False alarm. No moment taken - we're in the clear.",
            "relieved",
            LosingWarning::FalseAlarm as u16,
        ),
        _ => ("????", "neutral", Filler::Hrrm as u16),
    };

    handle_send_front_end_text_to_gecko(
        state,
        client_id,
        Some(json!({
            "message": message,
            "emotion": emotion,
            "unique_emotion_code": unique_emotion_code,
            "kind": kind,
            "ref_id": ref_id,
        })),
    )
    .await;
}

async fn handle_send_read_status_to_gecko(
    state: &AppState,
    client_id: &str,
    data: Option<Value>,
) {
    let payload = data.unwrap_or_else(|| json!({}));
    let code = payload.get("message_code").and_then(|v| v.as_i64());
    let kind = payload.get("kind").cloned();
    let ref_id = payload.get("ref_id").cloned();

    let (message, emotion, unique_emotion_code) = match code {
        Some(0) => (
            "Hi! I'm going to start reading this, if ya don't mind!",
            "cheerful",
            ReadStatus::Hi as u16,
        ),
        Some(1) => (
            "Still have some to read...",
            "concentrating",
            ReadStatus::StillReading as u16,
        ),
        Some(2) => ("Read em all!", "proud", ReadStatus::AllRead as u16),
        _ => ("Hrrrrrmmm hmmmmmmmm", "neutral", Filler::Hrrm as u16),
    };

    handle_send_front_end_text_to_gecko(
        state,
        client_id,
        Some(json!({
            "message": message,
            "emotion": emotion,
            "unique_emotion_code": unique_emotion_code,
            "kind": kind,
            "ref_id": ref_id,
        })),
    )
    .await;
}

async fn handle_get_gecko_screen_position(state: &AppState, client_id: &str) {
    let client = get_client(state, client_id).await;
    let Some(client) = client else { return };

    send_to_client(
        state,
        client_id,
        OutgoingMessage {
            action: "gecko_coords".to_string(),
            data: json!({
                "from_user": client.user_id,
                "position": [],
            }),
        },
    )
    .await;
}

async fn handle_update_gecko_position(state: &AppState, client_id: &str, data: Option<Value>) {
    let mut payload = data.unwrap_or_else(|| json!({}));

    let clients = state.clients.read().await;
    let Some(c) = clients.get(client_id) else { return };
    if c.friend_id.is_none() || !sesh_presence_allowed(c) {
        return;
    }
    let user_id = c.user_id;
    let friend_id = c.friend_id;
    let shared_room = c.shared_room.clone();

    if let Value::Object(map) = &mut payload {
        map.entry("position".to_string()).or_insert_with(|| json!([0, 0]));
        map.entry("energy".to_string()).or_insert_with(|| json!(1.0));
        map.insert("from_user".to_string(), json!(user_id));
        map.insert("friend_id".to_string(), json!(friend_id));
    }

    let Some(encoded) = encode_outgoing(&OutgoingMessage {
        action: "gecko_coords".to_string(),
        data: payload,
    }) else {
        return;
    };

    broadcast_position_to_room(state, &clients, &shared_room, user_id, "gecko_coords", encoded).await;
}

async fn handle_update_host_gecko_position(
    state: &AppState,
    client_id: &str,
    data: Option<Value>,
) {
    let mut payload = data.unwrap_or_else(|| json!({}));

    let clients = state.clients.read().await;
    let Some(c) = clients.get(client_id) else { return };
    if !c.is_host || !sesh_presence_allowed(c) {
        return;
    }
    let user_id = c.user_id;
    let friend_id = c.friend_id;
    let shared_room = c.shared_room.clone();

    if let Value::Object(map) = &mut payload {
        map.entry("position".to_string()).or_insert_with(|| json!([0, 0]));
        map.entry("steps".to_string()).or_insert_with(|| json!([]));
        map.entry("first_fingers".to_string()).or_insert_with(|| json!([]));
        map.entry("held_moments".to_string()).or_insert_with(|| json!([]));
        map.entry("moments".to_string()).or_insert_with(|| json!([]));
        map.entry("energy".to_string()).or_insert_with(|| json!(1.0));
        map.insert("from_user".to_string(), json!(user_id));
        map.insert("friend_id".to_string(), json!(friend_id));
    }

    let Some(encoded) = encode_outgoing(&OutgoingMessage {
        action: "host_gecko_coords".to_string(),
        data: payload,
    }) else {
        return;
    };

    broadcast_position_to_room(state, &clients, &shared_room, user_id, "host_gecko_coords", encoded).await;
}

async fn handle_update_guest_gecko_position(
    state: &AppState,
    client_id: &str,
    data: Option<Value>,
) {
    let mut payload = data.unwrap_or_else(|| json!({}));

    let clients = state.clients.read().await;
    let Some(c) = clients.get(client_id) else { return };
    if c.is_host || !sesh_presence_allowed(c) {
        return;
    }
    let user_id = c.user_id;
    let shared_room = c.shared_room.clone();

    if let Value::Object(map) = &mut payload {
        map.entry("position".to_string()).or_insert_with(|| json!([0, 0]));
        map.entry("steps".to_string()).or_insert_with(|| json!([]));
        map.entry("energy".to_string()).or_insert_with(|| json!(1.0));
        map.insert("from_user".to_string(), json!(user_id));
    }

    let Some(encoded) = encode_outgoing(&OutgoingMessage {
        action: "guest_gecko_coords".to_string(),
        data: payload,
    }) else {
        return;
    };

    broadcast_position_to_room(state, &clients, &shared_room, user_id, "guest_gecko_coords", encoded).await;
}

async fn handle_update_capsule_progress(
    state: &AppState,
    client_id: &str,
    data: Option<Value>,
) {
    let mut payload = data.unwrap_or_else(|| json!({}));
    let Value::Object(map) = &mut payload else { return };

    if !map.contains_key("capsule_id") {
        return;
    }
    let Some(new_progress) = map.get("new_progress").and_then(|v| v.as_f64()) else {
        return;
    };
    let new_progress = new_progress as i64;

    let clients = state.clients.read().await;
    let Some(c) = clients.get(client_id) else { return };
    if !sesh_presence_allowed(c) {
        return;
    }
    let user_id = c.user_id;
    let shared_room = c.shared_room.clone();

    map.insert("new_progress".to_string(), json!(new_progress));
    map.insert("from_user".to_string(), json!(user_id));

    let Some(encoded) = encode_outgoing(&OutgoingMessage {
        action: "capsule_progress".to_string(),
        data: payload,
    }) else {
        return;
    };

    broadcast_to_room_with_clients(state, &clients, &shared_room, user_id, encoded).await;
}


#[tracing::instrument(skip(state, data), fields(client_id = %client_id, user_id))]
async fn handle_request_points(
    state: &AppState,
    client_id: &str,
    data: Option<Value>,
) {
    // get_client clones a snapshot and drops the lock, so we never hold the
    // clients read guard across the Django await / broadcast.
    let Some(client) = get_client(state, client_id).await else { return };
    tracing::Span::current().record("user_id", client.user_id);
    info!("handle_request_points: received, forwarding to Django");

    // Django is the authoritative scorer: it validates `code`/`proof`,
    // resolves the ScoreRule + multiplier, writes the ledger, and (only if
    // the peer is present, decided server-side via the friend_id gate)
    // accrues to the shared sesh scoreboard. It also pushes the partner's
    // oriented copy directly (notify_user). Rust just relays the requester's
    // copy back — same per-recipient model as update_gecko_data.
    let mut data_with_ctx = match data.unwrap_or_else(|| json!({})) {
        Value::Object(map) => map,
        _ => serde_json::Map::new(),
    };
    // friend_id is NOT injected here. The FE sends it window-consistently
    // (friend id when the peer is present for the accrual window, null
    // otherwise); the relay must pass it through untouched so Django
    // attributes faithfully. Substituting the bound friend here would
    // re-introduce solo / wrong-friend mis-attribution.
    if !data_with_ctx.contains_key("is_host") {
        data_with_ctx.insert("is_host".to_string(), json!(client.is_host));
    }

    let body = json!({
        "user_id": client.user_id,
        "action": "request_points",
        "data": Value::Object(data_with_ctx),
    });

    let body_bytes = match rmp_serde::to_vec_named(&body) {
        Ok(b) => b,
        Err(err) => {
            error!("handle_request_points: msgpack encode failed err={}", err);
            send_to_client(
                state,
                client_id,
                OutgoingMessage {
                    action: "request_points_failed".to_string(),
                    data: json!({ "reason": "encode_error" }),
                },
            )
            .await;
            return;
        }
    };

    let url = format!("{}/users/internal/gecko/socket-action/", state.django_base_url);
    let _permit = state.django_concurrency.acquire().await.ok();
    let response = state
        .http
        .post(url)
        .header("X-Rust-Internal-Secret", &state.internal_secret)
        .header("Content-Type", "application/msgpack")
        .header("Accept", "application/msgpack")
        .body(body_bytes)
        .send()
        .await;

    let Ok(response) = response else {
        send_to_client(
            state,
            client_id,
            OutgoingMessage {
                action: "request_points_failed".to_string(),
                data: json!({ "reason": "django_unreachable" }),
            },
        )
        .await;
        return;
    };

    let Ok(bytes) = response.bytes().await else {
        send_to_client(
            state,
            client_id,
            OutgoingMessage {
                action: "request_points_failed".to_string(),
                data: json!({ "reason": "django_unreachable" }),
            },
        )
        .await;
        return;
    };

    let parsed: Result<Value, _> = rmp_serde::from_slice(&bytes);
    match parsed {
        Ok(value) => {
            let response_action = value
                .get("action")
                .and_then(|v| v.as_str())
                .unwrap_or("points_awarded")
                .to_string();
            let response_data = value.get("data").cloned().unwrap_or(value);

            // Relay the requester's oriented copy back to them only. The
            // partner's oriented copy is pushed by Django (notify_user),
            // same per-recipient pattern as the points_update flow.
            send_to_client(
                state,
                client_id,
                OutgoingMessage {
                    action: response_action,
                    data: response_data,
                },
            )
            .await;
        }
        Err(_) => {
            send_to_client(
                state,
                client_id,
                OutgoingMessage {
                    action: "request_points_failed".to_string(),
                    data: json!({ "reason": "bad_django_response" }),
                },
            )
            .await;
        }
    }
}

async fn handle_request_all_host_capsules(state: &AppState, client_id: &str) {
    let Some(client) = get_client(state, client_id).await else { return };
    if client.is_host { return }   // only guests should request
    broadcast_to_room(
        state,
        &client.shared_room,
        Some(client.user_id),
        OutgoingMessage {
            action: "request_all_host_capsules".to_string(),
            data: json!({ "from_user": client.user_id }),
        },
    ).await;
}

async fn handle_send_all_host_capsules(
    state: &AppState,
    client_id: &str,
    data: Option<Value>,
) {
    let mut payload = data.unwrap_or_else(|| json!({}));

    let clients = state.clients.read().await;
    let Some(c) = clients.get(client_id) else { return };
    if !c.is_host || !sesh_presence_allowed(c) {
        return;
    }
    let user_id = c.user_id;
    let friend_id = c.friend_id;
    let shared_room = c.shared_room.clone();

    if let Value::Object(map) = &mut payload {
        map.entry("moments".to_string()).or_insert_with(|| json!([]));
        map.insert("from_user".to_string(), json!(user_id));
        map.insert("friend_id".to_string(), json!(friend_id));
    }

    let Some(encoded) = encode_outgoing(&OutgoingMessage {
        action: "all_host_capsules".to_string(),
        data: payload,
    }) else {
        return;
    };

    broadcast_to_room_with_clients(state, &clients, &shared_room, user_id, encoded).await;
}

async fn proxy_check_host_link_and_load(
    state: &AppState,
    client_id: &str,
    partner_id: UserId,
) {
    let client = get_client(state, client_id).await;
    let Some(client) = client else { return };

    let url = format!(
        "{}/users/internal/gecko/check-host-link-and-load/",
        state.django_base_url
    );

    let _permit = state.django_concurrency.acquire().await.ok();
    let response = state
        .http
        .post(url)
        .header("X-Rust-Internal-Secret", &state.internal_secret)
        .json(&json!({
            "user_id": client.user_id,
            "partner_id": partner_id,
        }))
        .send()
        .await;

    let Ok(response) = response else {
        send_to_client(
            state,
            client_id,
            OutgoingMessage {
                action: "capsule_matches_ready".to_string(),
                data: json!({
                    "completed": false,
                    "reason": "django_unreachable",
                }),
            },
        )
        .await;
        return;
    };

    let parsed: Result<Value, _> = response.json().await;

    match parsed {
        Ok(value) => {
            let action = value
                .get("action")
                .and_then(|v| v.as_str())
                .unwrap_or("capsule_matches_ready")
                .to_string();

            let data = value.get("data").cloned().unwrap_or(value);

            send_to_client(state, client_id, OutgoingMessage { action, data }).await;
        }
        Err(_) => {
            send_to_client(
                state,
                client_id,
                OutgoingMessage {
                    action: "capsule_matches_ready".to_string(),
                    data: json!({
                        "completed": false,
                        "reason": "bad_django_response",
                    }),
                },
            )
            .await;
        }
    }
}

#[tracing::instrument(skip(state, data), fields(action = %action, user_id))]
async fn proxy_action_to_django(
    state: &AppState,
    client_id: &str,
    action: &str,
    data: Option<Value>,
) {
    let client = get_client(state, client_id).await;
    let Some(client) = client else { return };

    tracing::Span::current().record("user_id", client.user_id);

    let url = format!("{}/users/internal/gecko/socket-action/", state.django_base_url);

    let mut data_with_ctx = match data.unwrap_or_else(|| json!({})) {
        Value::Object(map) => map,
        _ => serde_json::Map::new(),
    };

    if !data_with_ctx.contains_key("friend_id") {
        if let Some(fid) = client.friend_id {
            data_with_ctx.insert("friend_id".to_string(), json!(fid));
        }
    }

    if !data_with_ctx.contains_key("is_host") {
        data_with_ctx.insert("is_host".to_string(), json!(client.is_host));
    }
    
    let payload = json!({
        "user_id": client.user_id,
        "action": action,
        "data": Value::Object(data_with_ctx),
    });

    let body_bytes = match rmp_serde::to_vec_named(&payload) {
        Ok(b) => b,
        Err(err) => {
            error!(
                "proxy_action_to_django: msgpack encode failed action={} err={}",
                action, err
            );
            send_to_client(
                state,
                client_id,
                OutgoingMessage {
                    action: format!("{}_failed", action),
                    data: json!({ "reason": "encode_error" }),
                },
            )
            .await;
            return;
        }
    };

    let _permit = state.django_concurrency.acquire().await.ok();
    let response = state
        .http
        .post(url)
        .header("X-Rust-Internal-Secret", &state.internal_secret)
        .header("Content-Type", "application/msgpack")
        .header("Accept", "application/msgpack")
        .body(body_bytes)
        .send()
        .await;

    let Ok(response) = response else {
        send_to_client(
            state,
            client_id,
            OutgoingMessage {
                action: format!("{}_failed", action),
                data: json!({ "reason": "django_unreachable" }),
            },
        )
        .await;
        return;
    };

    let bytes = match response.bytes().await {
        Ok(b) => b,
        Err(_) => {
            send_to_client(
                state,
                client_id,
                OutgoingMessage {
                    action: format!("{}_failed", action),
                    data: json!({ "reason": "django_unreachable" }),
                },
            )
            .await;
            return;
        }
    };

    let parsed: Result<Value, _> = rmp_serde::from_slice(&bytes);

    match parsed {
        Ok(value) => {
            let response_action = value
                .get("action")
                .and_then(|v| v.as_str())
                .unwrap_or(action)
                .to_string();

            let response_data = value.get("data").cloned().unwrap_or(value);

            send_to_client(
                state,
                client_id,
                OutgoingMessage {
                    action: response_action,
                    data: response_data,
                },
            )
            .await;
        }
        Err(_) => {
            send_to_client(
                state,
                client_id,
                OutgoingMessage {
                    action: format!("{}_failed", action),
                    data: json!({ "reason": "bad_django_response" }),
                },
            )
            .await;
        }
    }
}

// async fn handle_get_gecko_wins(state: &AppState, client_id: &str) {

//     let client = get_client(state, client_id).await;
//     let Some(client) = client else {return};
//     let user_id = client.user_id;

//     let cache_key = format!("")
// }

async fn handle_get_24h_seed(state: &AppState, client_id: &str) {
    // Hot path. Try Redis (sub-ms) first; only fall through to Django on a
    // cold cache. Django writes through this same key on every step bucket
    // update so steady state never leaves Rust + Redis.
    let client = get_client(state, client_id).await;
    let Some(client) = client else { return };
    let user_id = client.user_id;

    let cache_key = format!("gecko_24h:{}", user_id);
    let mut redis = state.redis.clone();
    if let Ok(Some(json_str)) = redis.get::<_, Option<String>>(&cache_key).await {
        if let Ok(value) = serde_json::from_str::<Value>(&json_str) {
            send_to_client(
                state,
                client_id,
                OutgoingMessage {
                    action: "seed_24h".to_string(),
                    data: value,
                },
            )
            .await;
            return;
        }
    }

    // Cold cache → fall through to Django (which will populate Redis on the
    // way out).
    proxy_action_to_django(state, client_id, "get_24h_seed", None).await;
}


async fn hydrate_live_sesh_context(
    state: &AppState,
    client_id: &str,
) {
    let client = get_client(state, client_id).await;
    let Some(client) = client else { return };
    let user_id = client.user_id;

    let cache_key = format!("gecko_sesh:{}", user_id);
    let mut redis = state.redis.clone();
    match redis.get::<_, Option<String>>(&cache_key).await {
        Ok(Some(json_str)) => {
            match serde_json::from_str::<Value>(&json_str) {
                Ok(value) => {
                    debug!(
                        target: "hydrate_live_sesh_context",
                        "cache hit user_id={}",
                        user_id
                    );
                    apply_hydrate_value(state, client_id, user_id, value).await;
                    return;
                }
                Err(e) => warn!(
                    target: "hydrate_live_sesh_context",
                    "cache value not parseable user_id={} err={}",
                    user_id, e
                ),
            }
        }
        Ok(None) => {}
        Err(e) => warn!(
            target: "hydrate_live_sesh_context",
            "redis get failed user_id={} err={}",
            user_id, e
        ),
    }

    let url = format!(
        "{}/users/internal/gecko/live-sesh-context/?user_id={}",
        state.django_base_url, user_id
    );

    let _permit = state.django_concurrency.acquire().await.ok();
    let response = state
        .http
        .get(url)
        .header("X-Rust-Internal-Secret", &state.internal_secret)
        .send()
        .await;

    let Ok(response) = response else {
        warn!(
            target: "hydrate_live_sesh_context",
            "django_unreachable user_id={}",
            user_id
        );
        return;
    };

    let parsed: Result<Value, _> = response.json().await;
    let Ok(value) = parsed else {
        warn!(
            target: "hydrate_live_sesh_context",
            "bad_django_response user_id={}",
            user_id
        );
        return;
    };

    apply_hydrate_value(state, client_id, user_id, value).await;
}

async fn apply_hydrate_value(
    state: &AppState,
    client_id: &str,
    user_id: UserId,
    value: Value,
) {
    let partner_id = value.get("partner_id").and_then(|v| v.as_u64());
    let is_host = value
        .get("is_host")
        .and_then(|v| v.as_bool())
        .unwrap_or(false);
    let friend_id = value.get("friend_id").and_then(|v| v.as_u64());
    let sesh_friend_id = value.get("sesh_friend_id").and_then(|v| v.as_u64());

    let friend_light_color = value
        .get("friend_light_color")
        .and_then(|v| v.as_str())
        .map(|s| s.to_string());

    let friend_dark_color = value
        .get("friend_dark_color")
        .and_then(|v| v.as_str())
        .map(|s| s.to_string());

    let gecko_game_level = value
        .get("gecko_game_level")
        .and_then(|v| v.as_u64())
        .map(|n| n as u16);

    let partner_username = value
        .get("partner_username")
        .and_then(|v| v.as_str())
        .map(|s| s.to_string());

    let partner_friend_id = value
        .get("partner_friend_id")
        .and_then(|v| v.as_u64());

    let partner_friend_name = value
        .get("partner_friend_name")
        .and_then(|v| v.as_str())
        .map(|s| s.to_string());

    let my_points = value.get("my_points").and_then(|v| v.as_u64()).unwrap_or(0);
    let partner_points = value
        .get("partner_points")
        .and_then(|v| v.as_u64())
        .unwrap_or(0);

    let my_wins = value.get("my_wins").and_then(|v| v.as_u64()).unwrap_or(0);
    let partner_wins = value
        .get("partner_wins")
        .and_then(|v| v.as_u64())
        .unwrap_or(0);

    let partner_room = partner_id.map(|pid| format!("gecko_shared_with_friend_{}", pid));

    {
        let mut clients = state.clients.write().await;
        if let Some(c) = clients.get_mut(client_id) {
            if partner_id.is_some() {
                c.partner_id = partner_id;
                c.is_host = is_host;
                c.sesh_friend_id = sesh_friend_id;
                c.partner_username = partner_username;
                c.partner_friend_id = partner_friend_id;
                c.partner_friend_name = partner_friend_name;
                c.my_points = my_points;
                c.partner_points = partner_points;
                c.my_wins = my_wins;
                c.partner_wins = partner_wins;
                c.partner_room = partner_room.clone();
                // Do NOT seed c.friend_id from hydrate for hosts. Hosts must
                // confirm via set_friend so we can verify they're on the
                // matching FE screen. Guests don't send set_friend, so we
                // populate from hydrate for them (so position handlers that
                // gate on friend_id still work).
                if !is_host && friend_id.is_some() {
                    c.friend_id = friend_id;
                }
                if friend_light_color.is_some() {
                    c.friend_light_color = friend_light_color;
                }
                if friend_dark_color.is_some() {
                    c.friend_dark_color = friend_dark_color;
                }
                if gecko_game_level.is_some() {
                    c.gecko_game_level = gecko_game_level;
                }
            }
        }
    }

    // Bind into the partner's shared room only once the client is sesh-present
    // (sesh_presence_allowed). Hosts confirm via set_friend and guests via
    // set_guest_on_screen, each of which performs the join on success. At
    // hydrate neither a host (no friend_id yet) nor a guest (not on-screen yet)
    // is present, so they intentionally don't join here.
    if let Some(room) = &partner_room {
        let allowed = {
            let clients = state.clients.read().await;
            clients
                .get(client_id)
                .map(sesh_presence_allowed)
                .unwrap_or(false)
        };
        if allowed {
            join_room(state, room, client_id).await;
        }
    }

    debug!(
        target: "hydrate_live_sesh_context",
        "user={} partner_id={:?} is_host={} friend_id={:?} partner_room={:?}",
        user_id,
        partner_id,
        is_host,
        friend_id,
        partner_room
    );
}

async fn disconnect_cleanup(state: &AppState, client_id: &str) {
    let client = get_client(state, client_id).await;

    if let Some(client) = client {

        debug!(
            target: "peer_pres",
            "disconnect_cleanup user={} broadcasting offline to {}",
            client.user_id, client.shared_room
        );

        broadcast_to_room(
            state,
            &client.shared_room,
            Some(client.user_id),
            OutgoingMessage {
                action: "peer_presence".to_string(),
                data: json!({
                    "user_id": client.user_id,
                    "online": false,
                    "friend_light_color": null,
                    "friend_dark_color": null,
                    "gecko_game_level": null,
                }),
            },
        )
        .await;
    }

    {
        let mut clients = state.clients.write().await;
        clients.remove(client_id);
    }

    {
        let mut rooms = state.rooms.write().await;
        for arc in rooms.values_mut() {
            Arc::make_mut(arc).remove(client_id);
        }
        rooms.retain(|_, set| !set.is_empty());
    }
}

async fn evict_existing_user(state: &AppState, user_id: UserId) {
    let to_evict: Vec<(ClientId, Tx)> = {
        let clients = state.clients.read().await;
        clients
            .iter()
            .filter(|(_, c)| c.user_id == user_id)
            .map(|(id, c)| (id.clone(), c.tx.clone()))
            .collect()
    };

    for (cid, tx) in to_evict {
        let warn = OutgoingMessage {
            action: "force_disconnect".to_string(),
            data: json!({ "reason": "superseded_by_new_connection" }),
        };

        if let Some(msg) = encode_outgoing(&warn) {
            // let _ = tx.send(msg);
            let _ = tx.try_send(msg);
        }

        // let _ = tx.send(Message::Close(None));
        let _ = tx.try_send(Message::Close(None));
        info!("evicting older socket for user_id={} client_id={}", user_id, cid);
    }
}

// async fn mark_seen(state: &AppState, client_id: &str) {
//     let mut clients = state.clients.write().await;
//     if let Some(client) = clients.get_mut(client_id) {
//         client.last_seen = Instant::now();
//     }
// }

async fn join_room(state: &AppState, room_name: &str, client_id: &str) {
    let mut rooms = state.rooms.write().await;
    let arc = rooms
        .entry(room_name.to_string())
        .or_insert_with(|| Arc::new(HashSet::new()));
    Arc::make_mut(arc).insert(client_id.to_string());
}


async fn leave_room(state: &AppState, room_name: &str, client_id: &str) {
    let mut rooms = state.rooms.write().await;
    if let Some(arc) = rooms.get_mut(room_name) {
        Arc::make_mut(arc).remove(client_id);
    }
    rooms.retain(|_, set| !set.is_empty());
}

/// Like broadcast_to_room, but only delivers to recipients where
/// sesh_presence_allowed is true — i.e., on-screen guests and hosts whose
/// FE-bound friend matches the sesh. Used for ONLINE peer_presence frames so a
/// host on a non-matching friend screen (or an off-screen guest) never sees
/// their partner painted as "online and in the sesh." OFFLINE frames should
/// keep using broadcast_to_room so they can clear stale state unconditionally.
async fn broadcast_peer_presence_online_to_room(
    state: &AppState,
    room_name: &str,
    exclude_user_id: Option<UserId>,
    message: OutgoingMessage,
) {
    let Some(encoded) = encode_outgoing(&message) else {
        return;
    };

    let room_client_ids = {
        let rooms = state.rooms.read().await;
        rooms.get(room_name).cloned()
    };

    let Some(room_client_ids) = room_client_ids else {
        return;
    };

    let clients = state.clients.read().await;

    for room_client_id in room_client_ids.iter() {
        if let Some(client) = clients.get(room_client_id) {
            if Some(client.user_id) == exclude_user_id {
                continue;
            }
            if !sesh_presence_allowed(client) {
                continue;
            }
            let _ = client.tx.try_send(encoded.clone());
        }
    }
}

/// A client is "in the sesh" (presence flows, frames are delivered) only when
/// their FE confirms they're on the correct screen. A host is bound when their
/// FE friend matches the sesh (friend_id == sesh_friend_id), confirmed via
/// set_friend. A guest is bound when their FE reports they're on the sesh
/// screen (guest_on_screen), confirmed via set_guest_on_screen. The two are
/// exact analogs — neither side is present until its FE confirms.
fn sesh_presence_allowed(c: &Client) -> bool {
    if !c.is_host {
        return c.guest_on_screen;
    }
    c.friend_id.is_some() && c.friend_id == c.sesh_friend_id
}

async fn get_client(state: &AppState, client_id: &str) -> Option<Client> {
    let clients = state.clients.read().await;
    clients.get(client_id).cloned()
}

async fn send_to_client(state: &AppState, client_id: &str, message: OutgoingMessage) {
    let clients = state.clients.read().await;
    if let Some(client) = clients.get(client_id) {
        send_outgoing(&client.tx, message);
    }
}

async fn broadcast_to_room(
    state: &AppState,
    room_name: &str,
    exclude_user_id: Option<UserId>,
    message: OutgoingMessage,
) {
    let Some(encoded) = encode_outgoing(&message) else {
        return;
    };

    let room_client_ids = {
        let rooms = state.rooms.read().await;
        rooms.get(room_name).cloned()   // <-- now clones the Arc, not the HashSet
    };

    let Some(room_client_ids) = room_client_ids else {
        return;
    };

    let clients = state.clients.read().await;

    for room_client_id in room_client_ids.iter() {
        if let Some(client) = clients.get(room_client_id) {
            if Some(client.user_id) == exclude_user_id {
                continue;
            }

            // let _ = client.tx.send(encoded.clone());
            let _ = client.tx.try_send(encoded.clone());

        }
    }
}

/// Broadcast a position frame to a room, routing each recipient through
/// their PositionSlots so older pending coords are overwritten by newer
/// ones (latest-wins). Bypasses the ordered mpsc entirely.
async fn broadcast_position_to_room(
    state: &AppState,
    clients: &HashMap<ClientId, Client>,
    room_name: &str,
    exclude_user_id: UserId,
    action: &str,
    encoded: Message,
) {
    debug_assert!(is_coalesced_position_action(action));
    let rooms = state.rooms.read().await;
    if let Some(room_arc) = rooms.get(room_name) {
        for cid in room_arc.iter() {
            if let Some(client) = clients.get(cid) {
                if client.user_id == exclude_user_id {
                    continue;
                }
                client.position_slots.put(action, encoded.clone());
            }
        }
    }
}

async fn broadcast_to_room_with_clients(
    state: &AppState,
    clients: &HashMap<ClientId, Client>,
    room_name: &str,
    exclude_user_id: UserId,
    encoded: Message,
) {
    let rooms = state.rooms.read().await;
    if let Some(room_arc) = rooms.get(room_name) {
        for cid in room_arc.iter() {
            if let Some(client) = clients.get(cid) {
                if client.user_id == exclude_user_id {
                    continue;
                }
                let _ = client.tx.try_send(encoded.clone());
            }
        }
    }
}

fn send_outgoing(tx: &Tx, message: OutgoingMessage) {
    if let Some(msg) = encode_outgoing(&message) {
        // let _ = tx.send(msg);
        let _ = tx.try_send(msg);
    }
}

fn encode_outgoing(message: &OutgoingMessage) -> Option<Message> {
    if BINARY_OUTBOUND_ACTIONS.contains(&message.action.as_str()) {
        match rmp_serde::to_vec_named(message) {
            Ok(bytes) => Some(Message::Binary(bytes.into())),
            Err(err) => {
                error!("failed to encode msgpack action={}: {}", message.action, err);
                None
            }
        }
    } else {
        match serde_json::to_string(message) {
            Ok(s) => Some(Message::Text(s.into())),
            Err(err) => {
                error!("failed to encode json action={}: {}", message.action, err);
                None
            }
        }
    }
}

fn check_internal_auth(state: &AppState, headers: &HeaderMap) -> Result<(), StatusCode> {
    if state.internal_secret.is_empty() {
        return Err(StatusCode::UNAUTHORIZED);
    }

    let provided = headers
        .get("X-Rust-Internal-Secret")
        .and_then(|v| v.to_str().ok())
        .unwrap_or("");

    if provided == state.internal_secret {
        Ok(())
    } else {
        Err(StatusCode::UNAUTHORIZED)
    }
}

async fn internal_push_user(
    State(state): State<AppState>,
    headers: HeaderMap,
    Json(body): Json<PushUserBody>,
) -> impl IntoResponse {
    if let Err(code) = check_internal_auth(&state, &headers) {
        return code.into_response();
    }

    let txs: Vec<Tx> = {
        let clients = state.clients.read().await;
        clients
            .values()
            .filter(|c| c.user_id == body.user_id)
            .map(|c| c.tx.clone())
            .collect()
    };

    if txs.is_empty() {
        return (StatusCode::OK, Json(json!({ "delivered": 0 }))).into_response();
    }

    let outgoing = OutgoingMessage {
        action: body.action,
        data: body.data,
    };

    let Some(encoded) = encode_outgoing(&outgoing) else {
        return StatusCode::INTERNAL_SERVER_ERROR.into_response();
    };

    let mut delivered = 0usize;

    for tx in &txs {
        // if tx.send(encoded.clone()).is_ok() {
        if tx.try_send(encoded.clone()).is_ok() {
            delivered += 1;
        }
    }

    if body.close_after {
        for tx in &txs {
            // let _ = tx.send(Message::Close(None));
            let _ = tx.try_send(Message::Close(None));
        }
    }

    (StatusCode::OK, Json(json!({ "delivered": delivered }))).into_response()
}

async fn internal_push_room(
    State(state): State<AppState>,
    headers: HeaderMap,
    Json(body): Json<PushRoomBody>,
) -> impl IntoResponse {
    if let Err(code) = check_internal_auth(&state, &headers) {
        return code.into_response();
    }

    let outgoing = OutgoingMessage {
        action: body.action,
        data: body.data,
    };

    let Some(encoded) = encode_outgoing(&outgoing) else {
        return StatusCode::INTERNAL_SERVER_ERROR.into_response();
    };

    let room_client_ids = {
        let rooms = state.rooms.read().await;
        rooms.get(&body.room).cloned()
    };

    let Some(room_client_ids) = room_client_ids else {
        return (StatusCode::OK, Json(json!({ "delivered": 0 }))).into_response();
    };

    let clients = state.clients.read().await;
    let mut delivered = 0usize;

    for cid in room_client_ids.iter() {
        if let Some(c) = clients.get(cid) {
            if Some(c.user_id) == body.exclude_user_id {
                continue;
            }

            // if c.tx.send(encoded.clone()).is_ok() {
            if c.tx.try_send(encoded.clone()).is_ok() {
                delivered += 1;
            }
        }
    }

    (StatusCode::OK, Json(json!({ "delivered": delivered }))).into_response()
}

async fn internal_disconnect_user(
    State(state): State<AppState>,
    headers: HeaderMap,
    Json(body): Json<DisconnectUserBody>,
) -> impl IntoResponse {
    if let Err(code) = check_internal_auth(&state, &headers) {
        return code.into_response();
    }

    let txs: Vec<Tx> = {
        let clients = state.clients.read().await;
        clients
            .values()
            .filter(|c| c.user_id == body.user_id)
            .map(|c| c.tx.clone())
            .collect()
    };

    let count = txs.len();

    for tx in txs {
        // let _ = tx.send(Message::Close(None));
        let _ = tx.try_send(Message::Close(None));

    }

    (StatusCode::OK, Json(json!({ "closed": count }))).into_response()
}