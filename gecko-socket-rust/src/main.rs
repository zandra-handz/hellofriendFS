

// use axum::{
//     extract::{
//         ws::{Message, WebSocket, WebSocketUpgrade},
//         Query, State,
//     },
//     http::{HeaderMap, StatusCode},
//     response::IntoResponse,
//     routing::{get, post},
//     Json, Router,
// };
// use futures_util::{SinkExt, StreamExt};
// use serde::{Deserialize, Serialize};
// use serde_json::{json, Value};
// use std::{
//     collections::{HashMap, HashSet},
//     net::SocketAddr,
//     sync::Arc,
//     time::Instant,
// };
// use tokio::sync::{mpsc, RwLock};
// use uuid::Uuid;

// type UserId = u64;
// type ClientId = String;
// type RoomName = String;
// type Tx = mpsc::UnboundedSender<Message>;

// const DJANGO_BASE_URL: &str = "http://127.0.0.1:8000";

// // Actions that ship as msgpack binary to match consumers.py ormsgpack output.
// // Everything else stays JSON text.
// const BINARY_OUTBOUND_ACTIONS: &[&str] = &[
//     "gecko_coords",
//     "host_gecko_coords",
//     "guest_gecko_coords",
//     "all_host_capsules",
//     "capsule_progress",
// ];

// #[derive(Clone)]
// struct AppState {
//     clients: Arc<RwLock<HashMap<ClientId, Client>>>,
//     rooms: Arc<RwLock<HashMap<RoomName, HashSet<ClientId>>>>,
//     http: reqwest::Client,
//     internal_secret: String,
// }

// #[derive(Clone)]
// struct Client {
//     user_id: UserId,
//     tx: Tx,
//     friend_id: Option<u64>,
//     is_host: bool,
//     partner_id: Option<u64>,
//     partner_username: Option<String>,
//     partner_friend_id: Option<u64>,
//     partner_friend_name: Option<String>,
//     sesh_friend_id: Option<u64>,
//     own_room: RoomName,
//     shared_room: RoomName,
//     partner_room: Option<RoomName>,
//     friend_light_color: Option<String>,
//     friend_dark_color: Option<String>,
//     gecko_message: Option<String>,
//     last_seen: Instant,
// }

// #[derive(Debug, Deserialize)]
// struct WsQuery {
//     user_id: Option<UserId>,
// }

// #[derive(Debug, Serialize)]
// struct OutgoingMessage {
//     action: String,
//     data: Value,
// }

// #[derive(Debug, Deserialize)]
// struct PushUserBody {
//     user_id: UserId,
//     action: String,
//     data: Value,
//     #[serde(default)]
//     close_after: bool,
// }

// #[derive(Debug, Deserialize)]
// struct PushRoomBody {
//     room: String,
//     action: String,
//     data: Value,
//     #[serde(default)]
//     exclude_user_id: Option<UserId>,
// }

// #[derive(Debug, Deserialize)]
// struct DisconnectUserBody {
//     user_id: UserId,
// }

// #[tokio::main]
// async fn main() {
//     let state = AppState {
//         clients: Arc::new(RwLock::new(HashMap::new())),
//         rooms: Arc::new(RwLock::new(HashMap::new())),
//         http: reqwest::Client::new(),
//         internal_secret: std::env::var("RUST_INTERNAL_SECRET").unwrap_or_default(),
//     };

//     if state.internal_secret.is_empty() {
//         println!("WARNING: RUST_INTERNAL_SECRET is empty — internal push routes will reject all calls");
//     }

//     let app = Router::new()
//         .route("/", get(root))
//         .route("/ws/gecko-rust-test", get(ws_handler))
//         .route("/ws/gecko-rust-test/", get(ws_handler))
//         .route("/internal/push/user", post(internal_push_user))
//         .route("/internal/push/room", post(internal_push_room))
//         .route("/internal/disconnect-user", post(internal_disconnect_user))
//         .with_state(state);

//     let addr = SocketAddr::from(([127, 0, 0, 1], 4000));
//     println!("Rust websocket running at http://{}", addr);

//     let listener = tokio::net::TcpListener::bind(addr)
//         .await
//         .expect("failed to bind Rust websocket server");

//     axum::serve(listener, app)
//         .await
//         .expect("Rust websocket server crashed");
// }

// async fn root() -> &'static str {
//     "rust socket server is running"
// }

// async fn ws_handler(
//     ws: WebSocketUpgrade,
//     Query(query): Query<WsQuery>,
//     State(state): State<AppState>,
// ) -> impl IntoResponse {
//     ws.on_upgrade(move |socket| handle_socket(socket, query, state))
// }

// async fn handle_socket(socket: WebSocket, query: WsQuery, state: AppState) {
//     let Some(user_id) = query.user_id else {
//         println!("rejecting websocket: missing user_id");
//         return;
//     };

//     // Single-active-channel: kick any older socket(s) for this user before
//     // registering the new one (mirrors consumer's force_disconnect path).
//     evict_existing_user(&state, user_id).await;

//     let client_id = Uuid::new_v4().to_string();
//     let own_room = format!("gecko_energy_{}", user_id);
//     let shared_room = format!("gecko_shared_with_friend_{}", user_id);

//     let (mut socket_sender, mut socket_receiver) = socket.split();
//     let (tx, mut rx) = mpsc::unbounded_channel::<Message>();

//     {
//         let mut clients = state.clients.write().await;
//         clients.insert(
//             client_id.clone(),
//             Client {
//                 user_id,
//                 tx: tx.clone(),
//                 friend_id: None,
//                 is_host: false,
//                 partner_id: None,
//                 partner_username: None,
//                 partner_friend_id: None,
//                 partner_friend_name: None,
//                 sesh_friend_id: None,
//                 own_room: own_room.clone(),
//                 shared_room: shared_room.clone(),
//                 partner_room: None,
//                 friend_light_color: None,
//                 friend_dark_color: None,
//                 gecko_message: None,
//                 last_seen: Instant::now(),
//             },
//         );
//     }

//     join_room(&state, &own_room, &client_id).await;
//     join_room(&state, &shared_room, &client_id).await;

//     send_outgoing(
//         &tx,
//         OutgoingMessage {
//             action: "rust_connected".to_string(),
//             data: json!({
//                 "user_id": user_id,
//                 "client_id": client_id,
//                 "own_room": own_room,
//                 "shared_room": shared_room,
//             }),
//         },
//     );

//     // Hydrate from Django: pulls live-sesh state AND the initial score_state.
//     // The score_state push to FE happens inside hydrate_live_sesh_context.
//     hydrate_live_sesh_context(&state, &client_id, true).await;

//     let send_task = tokio::spawn(async move {
//         while let Some(message) = rx.recv().await {
//             let is_close = matches!(message, Message::Close(_));
//             if socket_sender.send(message).await.is_err() {
//                 break;
//             }
//             if is_close {
//                 break;
//             }
//         }
//     });

//     let recv_state = state.clone();
//     let recv_client_id = client_id.clone();

//     let recv_task = tokio::spawn(async move {
//         while let Some(result) = socket_receiver.next().await {
//             match result {
//                 Ok(Message::Text(text)) => {
//                     mark_seen(&recv_state, &recv_client_id).await;
//                     match serde_json::from_str::<Value>(&text) {
//                         Ok(value) => {
//                             handle_incoming(&recv_state, &recv_client_id, value).await;
//                         }
//                         Err(_) => {
//                             send_to_client(
//                                 &recv_state,
//                                 &recv_client_id,
//                                 OutgoingMessage {
//                                     action: "rust_error".to_string(),
//                                     data: json!({ "reason": "invalid_json", "raw": text.to_string() }),
//                                 },
//                             )
//                             .await;
//                         }
//                     }
//                 }
//                 Ok(Message::Binary(bytes)) => {
//                     mark_seen(&recv_state, &recv_client_id).await;
//                     match rmp_serde::from_slice::<Value>(&bytes) {
//                         Ok(value) => {
//                             handle_incoming(&recv_state, &recv_client_id, value).await;
//                         }
//                         Err(_) => {
//                             send_to_client(
//                                 &recv_state,
//                                 &recv_client_id,
//                                 OutgoingMessage {
//                                     action: "rust_error".to_string(),
//                                     data: json!({
//                                         "reason": "invalid_msgpack",
//                                         "bytes_len": bytes.len(),
//                                     }),
//                                 },
//                             )
//                             .await;
//                         }
//                     }
//                 }
//                 Ok(Message::Ping(_)) | Ok(Message::Pong(_)) => {
//                     mark_seen(&recv_state, &recv_client_id).await;
//                 }
//                 Ok(Message::Close(_)) => break,
//                 Err(err) => {
//                     println!("websocket error client_id={} err={}", recv_client_id, err);
//                     break;
//                 }
//             }
//         }
//     });

//     tokio::select! {
//         _ = send_task => {},
//         _ = recv_task => {},
//     }

//     disconnect_cleanup(&state, &client_id).await;
// }

// async fn handle_incoming(state: &AppState, client_id: &str, value: Value) {
//     let action = value
//         .get("action")
//         .and_then(|v| v.as_str())
//         .unwrap_or("")
//         .to_string();
//     let data = value.get("data").cloned();

//     match action.as_str() {
//         "ping" => {
//             send_to_client(
//                 state,
//                 client_id,
//                 OutgoingMessage {
//                     action: "pong".to_string(),
//                     data: json!({}),
//                 },
//             )
//             .await;
//         }

//         "set_friend" => handle_set_friend(state, client_id, data).await,
//         "join_live_sesh" => handle_join_live_sesh(state, client_id).await,
//         "leave_live_sesh" => handle_leave_live_sesh(state, client_id).await,
//         "request_peer_presence" => handle_request_peer_presence(state, client_id).await,

//         "get_gecko_message" => handle_get_gecko_message(state, client_id).await,
//         "send_front_end_text_to_gecko" => {
//             handle_send_front_end_text_to_gecko(state, client_id, data).await
//         }
//         "send_read_status_to_gecko" => {
//             handle_send_read_status_to_gecko(state, client_id, data).await
//         }

//         "get_gecko_screen_position" => handle_get_gecko_screen_position(state, client_id).await,
//         "update_gecko_position" => handle_update_gecko_position(state, client_id, data).await,
//         "update_host_gecko_position" => {
//             handle_update_host_gecko_position(state, client_id, data).await
//         }
//         "update_guest_gecko_position" => {
//             handle_update_guest_gecko_position(state, client_id, data).await
//         }
//         "update_capsule_progress" => {
//             handle_update_capsule_progress(state, client_id, data).await
//         }
//         "send_all_host_capsules" => {
//             handle_send_all_host_capsules(state, client_id, data).await
//         }

//         // Heavy server-side validation lives in Django. Rust just forwards.
//         // Django returns the direct ack; any peer broadcasts come back via
//         // the /internal/push/* routes.
//         "get_score_state"
//         | "update_gecko_data"
//         | "flush"
//         | "request_capsule_matches"
//         | "repull_capsule_matches"
//         | "send_match_request"
//         | "propose_gecko_win"
//         | "propose_gecko_match_win"
//         | "send_validate_win_request"
//         | "send_validate_match_win_request" => {
//             proxy_action_to_django(state, client_id, &action, data).await;
//         }

//         _ => {
//             send_to_client(
//                 state,
//                 client_id,
//                 OutgoingMessage {
//                     action: "rust_error".to_string(),
//                     data: json!({
//                         "reason": "unknown_action",
//                         "action": action,
//                     }),
//                 },
//             )
//             .await;
//         }
//     }
// }

// async fn handle_set_friend(state: &AppState, client_id: &str, data: Option<Value>) {
//     let payload = data.unwrap_or_else(|| json!({}));
//     let friend_id = payload.get("friend_id").and_then(|v| v.as_u64());

//     let Some(friend_id) = friend_id else {
//         send_to_client(
//             state,
//             client_id,
//             OutgoingMessage {
//                 action: "set_friend_failed".to_string(),
//                 data: json!({ "reason": "invalid_friend_id" }),
//             },
//         )
//         .await;
//         return;
//     };

//     // Mirror consumer's host/sesh check: if we're a host with a known
//     // sesh_friend_id, the FE-supplied friend_id has to match it.
//     let client_snap = get_client(state, client_id).await;
//     if let Some(c) = &client_snap {
//         if c.is_host {
//             if let Some(sfid) = c.sesh_friend_id {
//                 if sfid != friend_id {
//                     send_to_client(
//                         state,
//                         client_id,
//                         OutgoingMessage {
//                             action: "set_friend_failed".to_string(),
//                             data: json!({ "reason": "sesh_friend_mismatch" }),
//                         },
//                     )
//                     .await;
//                     return;
//                 }
//             }
//         }
//     }

//     {
//         let mut clients = state.clients.write().await;
//         if let Some(client) = clients.get_mut(client_id) {
//             client.friend_id = Some(friend_id);
//             client.friend_light_color = payload
//                 .get("friend_light_color")
//                 .and_then(|v| v.as_str())
//                 .map(|s| s.to_string());
//             client.friend_dark_color = payload
//                 .get("friend_dark_color")
//                 .and_then(|v| v.as_str())
//                 .map(|s| s.to_string());
//         }
//     }

//     send_to_client(
//         state,
//         client_id,
//         OutgoingMessage {
//             action: "set_friend_ok".to_string(),
//             data: json!({ "friend_id": friend_id }),
//         },
//     )
//     .await;
// }

// async fn handle_join_live_sesh(state: &AppState, client_id: &str) {
//     hydrate_live_sesh_context(state, client_id, false).await;

//     let client = get_client(state, client_id).await;
//     let Some(client) = client else { return };

//     let Some(partner_id) = client.partner_id else {
//         send_to_client(
//             state,
//             client_id,
//             OutgoingMessage {
//                 action: "join_live_sesh_failed".to_string(),
//                 data: json!({ "reason": "no_active_sesh" }),
//             },
//         )
//         .await;
//         return;
//     };

//     let partner_room = format!("gecko_shared_with_friend_{}", partner_id);
//     join_room(state, &partner_room, client_id).await;

//     {
//         let mut clients = state.clients.write().await;
//         if let Some(c) = clients.get_mut(client_id) {
//             c.partner_room = Some(partner_room.clone());
//         }
//     }

//     send_to_client(
//         state,
//         client_id,
//         OutgoingMessage {
//             action: "join_live_sesh_ok".to_string(),
//             data: json!({
//                 "partner_id": partner_id,
//                 "partner_username": client.partner_username,
//                 "partner_friend_id": client.partner_friend_id,
//                 "partner_friend_name": client.partner_friend_name,
//             }),
//         },
//     )
//     .await;

//     broadcast_to_room(
//         state,
//         &client.shared_room,
//         Some(client.user_id),
//         OutgoingMessage {
//             action: "peer_presence".to_string(),
//             data: json!({
//                 "user_id": client.user_id,
//                 "online": true,
//                 "friend_light_color": client.friend_light_color,
//                 "friend_dark_color": client.friend_dark_color,
//             }),
//         },
//     )
//     .await;

//     if !client.is_host {
//     proxy_check_host_link_and_load(state, client_id, partner_id).await;
// }
// }

// async fn handle_leave_live_sesh(state: &AppState, client_id: &str) {
//     let client = get_client(state, client_id).await;
//     let Some(client) = client else { return };

//     broadcast_to_room(
//         state,
//         &client.shared_room,
//         Some(client.user_id),
//         OutgoingMessage {
//             action: "peer_presence".to_string(),
//             data: json!({
//                 "user_id": client.user_id,
//                 "online": false,
//                 "friend_light_color": null,
//                 "friend_dark_color": null,
//             }),
//         },
//     )
//     .await;

//     if client.is_host {
//         broadcast_to_room(
//             state,
//             &client.shared_room,
//             Some(client.user_id),
//             OutgoingMessage {
//                 action: "host_gecko_coords".to_string(),
//                 data: json!({
//                     "from_user": client.user_id,
//                     "friend_id": client.friend_id,
//                     "position": [0, 0],
//                     "steps": [],
//                     "steps_len": 0,
//                     "first_fingers": [],
//                     "held_moments": [],
//                     "held_moments_len": 0,
//                     "moments": [],
//                     "moments_len": 0,
//                     "timestamp": null,
//                 }),
//             },
//         )
//         .await;
//     } else {
//         broadcast_to_room(
//             state,
//             &client.shared_room,
//             Some(client.user_id),
//             OutgoingMessage {
//                 action: "guest_gecko_coords".to_string(),
//                 data: json!({
//                     "from_user": client.user_id,
//                     "position": [0, 0],
//                     "steps": [],
//                     "timestamp": null,
//                 }),
//             },
//         )
//         .await;
//     }

//     if let Some(partner_room) = client.partner_room {
//         leave_room(state, &partner_room, client_id).await;
//     }

//     {
//         let mut clients = state.clients.write().await;
//         if let Some(c) = clients.get_mut(client_id) {
//             c.partner_room = None;
//             c.is_host = false;
//         }
//     }

//     send_to_client(
//         state,
//         client_id,
//         OutgoingMessage {
//             action: "leave_live_sesh_ok".to_string(),
//             data: json!({}),
//         },
//     )
//     .await;
// }

// async fn handle_request_peer_presence(state: &AppState, client_id: &str) {
//     let client = get_client(state, client_id).await;
//     let Some(client) = client else { return };

//     let Some(partner_room) = client.partner_room.clone() else {
//         send_to_client(
//             state,
//             client_id,
//             OutgoingMessage {
//                 action: "peer_presence".to_string(),
//                 data: json!({ "online": false }),
//             },
//         )
//         .await;
//         return;
//     };

//     broadcast_to_room(
//         state,
//         &partner_room,
//         Some(client.user_id),
//         OutgoingMessage {
//             action: "peer_presence_request".to_string(),
//             data: json!({
//                 "requester_user_id": client.user_id,
//             }),
//         },
//     )
//     .await;
// }

// async fn handle_get_gecko_message(state: &AppState, client_id: &str) {
//     let client = get_client(state, client_id).await;
//     let Some(client) = client else { return };

//     send_to_client(
//         state,
//         client_id,
//         OutgoingMessage {
//             action: "gecko_message".to_string(),
//             data: json!({
//                 "from_user": client.user_id,
//                 "message": client.gecko_message,
//             }),
//         },
//     )
//     .await;
// }

// async fn handle_send_front_end_text_to_gecko(
//     state: &AppState,
//     client_id: &str,
//     data: Option<Value>,
// ) {
//     let payload = data.unwrap_or_else(|| json!({}));
//     let message = payload
//         .get("message")
//         .and_then(|v| v.as_str())
//         .map(|s| s.to_string());

//     {
//         let mut clients = state.clients.write().await;
//         if let Some(client) = clients.get_mut(client_id) {
//             client.gecko_message = message.clone();
//         }
//     }

//     let client = get_client(state, client_id).await;
//     let Some(client) = client else { return };

//     send_to_client(
//         state,
//         client_id,
//         OutgoingMessage {
//             action: "gecko_message".to_string(),
//             data: json!({
//                 "from_user": client.user_id,
//                 "message": message,
//             }),
//         },
//     )
//     .await;
// }

// async fn handle_send_read_status_to_gecko(
//     state: &AppState,
//     client_id: &str,
//     data: Option<Value>,
// ) {
//     let payload = data.unwrap_or_else(|| json!({}));
//     let code = payload.get("message_code").and_then(|v| v.as_i64());

//     let message = match code {
//         Some(0) => "Hi! I'm going to start reading this, if ya don't mind!",
//         Some(1) => "Still have some to read...",
//         Some(2) => "Read em all!",
//         _ => "Hrrrrrmmm hmmmmmmmm",
//     }
//     .to_string();

//     handle_send_front_end_text_to_gecko(
//         state,
//         client_id,
//         Some(json!({ "message": message })),
//     )
//     .await;
// }

// async fn handle_get_gecko_screen_position(state: &AppState, client_id: &str) {
//     let client = get_client(state, client_id).await;
//     let Some(client) = client else { return };

//     send_to_client(
//         state,
//         client_id,
//         OutgoingMessage {
//             action: "gecko_coords".to_string(),
//             data: json!({
//                 "from_user": client.user_id,
//                 "position": [],
//             }),
//         },
//     )
//     .await;
// }

// async fn handle_update_gecko_position(state: &AppState, client_id: &str, data: Option<Value>) {
//     let client = get_client(state, client_id).await;
//     let Some(client) = client else { return };

//     if client.friend_id.is_none() {
//         return;
//     }

//     let payload = data.unwrap_or_else(|| json!({}));
//     let position = payload.get("position").cloned().unwrap_or_else(|| json!([0, 0]));

//     broadcast_to_room(
//         state,
//         &client.shared_room,
//         Some(client.user_id),
//         OutgoingMessage {
//             action: "gecko_coords".to_string(),
//             data: json!({
//                 "from_user": client.user_id,
//                 "friend_id": client.friend_id,
//                 "position": position,
//             }),
//         },
//     )
//     .await;
// }

// async fn handle_update_host_gecko_position(
//     state: &AppState,
//     client_id: &str,
//     data: Option<Value>,
// ) {
//     let client = get_client(state, client_id).await;
//     let Some(client) = client else { return };

//     if !client.is_host || client.friend_id.is_none() {
//         return;
//     }

//     let payload = data.unwrap_or_else(|| json!({}));

//     broadcast_to_room(
//         state,
//         &client.shared_room,
//         Some(client.user_id),
//         OutgoingMessage {
//             action: "host_gecko_coords".to_string(),
//             data: json!({
//                 "from_user": client.user_id,
//                 "friend_id": client.friend_id,
//                 "position": payload.get("position").cloned().unwrap_or_else(|| json!([0, 0])),
//                 "steps": payload.get("steps").cloned().unwrap_or_else(|| json!([])),
//                 "steps_len": payload.get("steps_len").cloned(),
//                 "first_fingers": payload.get("first_fingers").cloned().unwrap_or_else(|| json!([])),
//                 "held_moments": payload.get("held_moments").cloned().unwrap_or_else(|| json!([])),
//                 "held_moments_len": payload.get("held_moments_len").cloned(),
//                 "moments": payload.get("moments").cloned().unwrap_or_else(|| json!([])),
//                 "moments_len": payload.get("moments_len").cloned(),
//                 "timestamp": payload.get("timestamp").cloned(),
//             }),
//         },
//     )
//     .await;
// }

// async fn handle_update_guest_gecko_position(
//     state: &AppState,
//     client_id: &str,
//     data: Option<Value>,
// ) {
//     let client = get_client(state, client_id).await;
//     let Some(client) = client else { return };

//     if client.is_host {
//         return;
//     }

//     let payload = data.unwrap_or_else(|| json!({}));

//     broadcast_to_room(
//         state,
//         &client.shared_room,
//         Some(client.user_id),
//         OutgoingMessage {
//             action: "guest_gecko_coords".to_string(),
//             data: json!({
//                 "from_user": client.user_id,
//                 "position": payload.get("position").cloned().unwrap_or_else(|| json!([0, 0])),
//                 "steps": payload.get("steps").cloned().unwrap_or_else(|| json!([])),
//                 "timestamp": payload.get("timestamp").cloned(),
//             }),
//         },
//     )
//     .await;
// }

// async fn handle_update_capsule_progress(
//     state: &AppState,
//     client_id: &str,
//     data: Option<Value>,
// ) {
//     let client = get_client(state, client_id).await;
//     let Some(client) = client else { return };

//     let payload = data.unwrap_or_else(|| json!({}));
//     let capsule_id = payload.get("capsule_id").cloned();
//     let new_progress_raw = payload.get("new_progress").cloned();

//     let Some(capsule_id) = capsule_id else { return };
//     let Some(new_progress_raw) = new_progress_raw else { return };

//     // Match consumer: cast to int.
//     let new_progress = new_progress_raw.as_f64().map(|n| n as i64);
//     let Some(new_progress) = new_progress else { return };

//     broadcast_to_room(
//         state,
//         &client.shared_room,
//         Some(client.user_id),
//         OutgoingMessage {
//             action: "capsule_progress".to_string(),
//             data: json!({
//                 "from_user": client.user_id,
//                 "capsule_id": capsule_id,
//                 "new_progress": new_progress,
//                 "timestamp": payload.get("timestamp").cloned(),
//             }),
//         },
//     )
//     .await;
// }

// async fn handle_send_all_host_capsules(
//     state: &AppState,
//     client_id: &str,
//     data: Option<Value>,
// ) {
//     let client = get_client(state, client_id).await;
//     let Some(client) = client else { return };

//     if !client.is_host || client.friend_id.is_none() {
//         return;
//     }

//     let payload = data.unwrap_or_else(|| json!({}));

//     broadcast_to_room(
//         state,
//         &client.shared_room,
//         Some(client.user_id),
//         OutgoingMessage {
//             action: "all_host_capsules".to_string(),
//             data: json!({
//                 "from_user": client.user_id,
//                 "friend_id": client.friend_id,
//                 "moments": payload.get("moments").cloned().unwrap_or_else(|| json!([])),
//                 "moments_len": payload.get("moments_len").cloned(),
//                 "timestamp": payload.get("timestamp").cloned(),
//             }),
//         },
//     )
//     .await;
// }
// async fn proxy_check_host_link_and_load(
//     state: &AppState,
//     client_id: &str,
//     partner_id: UserId,
// ) {
//     let client = get_client(state, client_id).await;
//     let Some(client) = client else { return };

//     let url = format!(
//         "{}/users/internal/gecko/check-host-link-and-load/",
//         DJANGO_BASE_URL
//     );

//     let response = state
//         .http
//         .post(url)
//         .header("X-Rust-Internal-Secret", &state.internal_secret)
//         .json(&json!({
//             "user_id": client.user_id,
//             "partner_id": partner_id,
//         }))
//         .send()
//         .await;

//     let Ok(response) = response else {
//         send_to_client(
//             state,
//             client_id,
//             OutgoingMessage {
//                 action: "capsule_matches_ready".to_string(),
//                 data: json!({
//                     "completed": false,
//                     "reason": "django_unreachable",
//                 }),
//             },
//         )
//         .await;
//         return;
//     };

//     let parsed: Result<Value, _> = response.json().await;

//     match parsed {
//         Ok(value) => {
//             let action = value
//                 .get("action")
//                 .and_then(|v| v.as_str())
//                 .unwrap_or("capsule_matches_ready")
//                 .to_string();

//             let data = value
//                 .get("data")
//                 .cloned()
//                 .unwrap_or(value);

//             send_to_client(
//                 state,
//                 client_id,
//                 OutgoingMessage {
//                     action,
//                     data,
//                 },
//             )
//             .await;
//         }
//         Err(_) => {
//             send_to_client(
//                 state,
//                 client_id,
//                 OutgoingMessage {
//                     action: "capsule_matches_ready".to_string(),
//                     data: json!({
//                         "completed": false,
//                         "reason": "bad_django_response",
//                     }),
//                 },
//             )
//             .await;
//         }
//     }
// }


// async fn proxy_action_to_django(
//     state: &AppState,
//     client_id: &str,
//     action: &str,
//     data: Option<Value>,
// ) {
//     let client = get_client(state, client_id).await;
//     let Some(client) = client else { return };

//     let url = format!("{}/users/internal/gecko/socket-action/", DJANGO_BASE_URL);

//     // Inject server-tracked context the FE doesn't send (friend_id, is_host)
//     // so Django doesn't have to re-derive them. Don't overwrite caller-set
//     // keys — the FE may legitimately supply them.
//     let mut data_with_ctx = match data.unwrap_or_else(|| json!({})) {
//         Value::Object(map) => map,
//         _ => serde_json::Map::new(),
//     };
//     if !data_with_ctx.contains_key("friend_id") {
//         if let Some(fid) = client.friend_id {
//             data_with_ctx.insert("friend_id".to_string(), json!(fid));
//         }
//     }
//     if !data_with_ctx.contains_key("is_host") {
//         data_with_ctx.insert("is_host".to_string(), json!(client.is_host));
//     }

//     let response = state
//         .http
//         .post(url)
//         .header("X-Rust-Internal-Secret", &state.internal_secret)
//         .json(&json!({
//             "user_id": client.user_id,
//             "action": action,
//             "data": Value::Object(data_with_ctx),
//         }))
//         .send()
//         .await;

//     let Ok(response) = response else {
//         send_to_client(
//             state,
//             client_id,
//             OutgoingMessage {
//                 action: format!("{}_failed", action),
//                 data: json!({ "reason": "django_unreachable" }),
//             },
//         )
//         .await;
//         return;
//     };

//     let parsed: Result<Value, _> = response.json().await;

//     match parsed {
//         Ok(value) => {
//             let response_action = value
//                 .get("action")
//                 .and_then(|v| v.as_str())
//                 .unwrap_or(action)
//                 .to_string();

//             let response_data = value.get("data").cloned().unwrap_or(value);

//             send_to_client(
//                 state,
//                 client_id,
//                 OutgoingMessage {
//                     action: response_action,
//                     data: response_data,
//                 },
//             )
//             .await;
//         }
//         Err(_) => {
//             send_to_client(
//                 state,
//                 client_id,
//                 OutgoingMessage {
//                     action: format!("{}_failed", action),
//                     data: json!({ "reason": "bad_django_response" }),
//                 },
//             )
//             .await;
//         }
//     }
// }

// // `send_initial_score_state`: when called during connect, also forward the
// // score_state field (if present) to the freshly-connected client so the FE
// // gets the same first frame consumer.py sends right after accept().
// async fn hydrate_live_sesh_context(state: &AppState, client_id: &str, send_initial_score_state: bool) {
//     let client = get_client(state, client_id).await;
//     let Some(client) = client else { return };

//     let url = format!(
//         "{}/users/internal/gecko/live-sesh-context/?user_id={}",
//         DJANGO_BASE_URL, client.user_id
//     );

//     let response = state
//         .http
//         .get(url)
//         .header("X-Rust-Internal-Secret", &state.internal_secret)
//         .send()
//         .await;

//     let Ok(response) = response else {
//         return;
//     };

//     let parsed: Result<Value, _> = response.json().await;
//     let Ok(value) = parsed else {
//         return;
//     };

//     let partner_id = value.get("partner_id").and_then(|v| v.as_u64());
//     let is_host = value
//         .get("is_host")
//         .and_then(|v| v.as_bool())
//         .unwrap_or(false);
//     let friend_id = value.get("friend_id").and_then(|v| v.as_u64());
//     let sesh_friend_id = value.get("sesh_friend_id").and_then(|v| v.as_u64());

//     let friend_light_color = value
//         .get("friend_light_color")
//         .and_then(|v| v.as_str())
//         .map(|s| s.to_string());

//     let friend_dark_color = value
//         .get("friend_dark_color")
//         .and_then(|v| v.as_str())
//         .map(|s| s.to_string());

//     let partner_username = value
//         .get("partner_username")
//         .and_then(|v| v.as_str())
//         .map(|s| s.to_string());

//     let partner_friend_id = value.get("partner_friend_id").and_then(|v| v.as_u64());

//     let partner_friend_name = value
//         .get("partner_friend_name")
//         .and_then(|v| v.as_str())
//         .map(|s| s.to_string());

//     {
//         let mut clients = state.clients.write().await;
//         if let Some(c) = clients.get_mut(client_id) {
//             c.partner_id = partner_id;
//             c.is_host = is_host;
//             c.friend_id = friend_id;
//             c.sesh_friend_id = sesh_friend_id;
//             c.friend_light_color = friend_light_color;
//             c.friend_dark_color = friend_dark_color;
//             c.partner_username = partner_username;
//             c.partner_friend_id = partner_friend_id;
//             c.partner_friend_name = partner_friend_name;
//         }
//     }

//     if let Some(partner_id) = partner_id {
//         let partner_room = format!("gecko_shared_with_friend_{}", partner_id);
//         join_room(state, &partner_room, client_id).await;

//         let mut clients = state.clients.write().await;
//         if let Some(c) = clients.get_mut(client_id) {
//             c.partner_room = Some(partner_room);
//         }
//     }

//     if send_initial_score_state {
//         if let Some(score_state) = value.get("score_state").cloned() {
//             send_to_client(
//                 state,
//                 client_id,
//                 OutgoingMessage {
//                     action: "score_state".to_string(),
//                     data: score_state,
//                 },
//             )
//             .await;
//         }
//     }
// }

// async fn disconnect_cleanup(state: &AppState, client_id: &str) {
//     let client = get_client(state, client_id).await;

//     if let Some(client) = client {
//         broadcast_to_room(
//             state,
//             &client.shared_room,
//             Some(client.user_id),
//             OutgoingMessage {
//                 action: "peer_presence".to_string(),
//                 data: json!({
//                     "user_id": client.user_id,
//                     "online": false,
//                     "friend_light_color": null,
//                     "friend_dark_color": null,
//                 }),
//             },
//         )
//         .await;
//     }

//     {
//         let mut clients = state.clients.write().await;
//         clients.remove(client_id);
//     }

//     {
//         let mut rooms = state.rooms.write().await;
//         for set in rooms.values_mut() {
//             set.remove(client_id);
//         }
//         rooms.retain(|_, set| !set.is_empty());
//     }
// }

// async fn evict_existing_user(state: &AppState, user_id: UserId) {
//     let to_evict: Vec<(ClientId, Tx)> = {
//         let clients = state.clients.read().await;
//         clients
//             .iter()
//             .filter(|(_, c)| c.user_id == user_id)
//             .map(|(id, c)| (id.clone(), c.tx.clone()))
//             .collect()
//     };

//     for (cid, tx) in to_evict {
//         // Best-effort warning frame so the FE knows it was kicked, then close.
//         let warn = OutgoingMessage {
//             action: "force_disconnect".to_string(),
//             data: json!({ "reason": "superseded_by_new_connection" }),
//         };
//         if let Some(msg) = encode_outgoing(&warn) {
//             let _ = tx.send(msg);
//         }
//         let _ = tx.send(Message::Close(None));
//         println!("evicting older socket for user_id={} client_id={}", user_id, cid);
//     }
// }

// async fn mark_seen(state: &AppState, client_id: &str) {
//     let mut clients = state.clients.write().await;
//     if let Some(client) = clients.get_mut(client_id) {
//         client.last_seen = Instant::now();
//     }
// }

// async fn join_room(state: &AppState, room_name: &str, client_id: &str) {
//     let mut rooms = state.rooms.write().await;
//     rooms
//         .entry(room_name.to_string())
//         .or_insert_with(HashSet::new)
//         .insert(client_id.to_string());
// }

// async fn leave_room(state: &AppState, room_name: &str, client_id: &str) {
//     let mut rooms = state.rooms.write().await;
//     if let Some(set) = rooms.get_mut(room_name) {
//         set.remove(client_id);
//     }
//     rooms.retain(|_, set| !set.is_empty());
// }

// async fn get_client(state: &AppState, client_id: &str) -> Option<Client> {
//     let clients = state.clients.read().await;
//     clients.get(client_id).cloned()
// }

// async fn send_to_client(state: &AppState, client_id: &str, message: OutgoingMessage) {
//     let clients = state.clients.read().await;
//     if let Some(client) = clients.get(client_id) {
//         send_outgoing(&client.tx, message);
//     }
// }

// async fn broadcast_to_room(
//     state: &AppState,
//     room_name: &str,
//     exclude_user_id: Option<UserId>,
//     message: OutgoingMessage,
// ) {
//     let Some(encoded) = encode_outgoing(&message) else {
//         return;
//     };

//     let room_client_ids = {
//         let rooms = state.rooms.read().await;
//         rooms.get(room_name).cloned()
//     };

//     let Some(room_client_ids) = room_client_ids else {
//         return;
//     };

//     let clients = state.clients.read().await;

//     for room_client_id in room_client_ids {
//         if let Some(client) = clients.get(&room_client_id) {
//             if Some(client.user_id) == exclude_user_id {
//                 continue;
//             }
//             let _ = client.tx.send(encoded.clone());
//         }
//     }
// }

// fn send_outgoing(tx: &Tx, message: OutgoingMessage) {
//     if let Some(msg) = encode_outgoing(&message) {
//         let _ = tx.send(msg);
//     }
// }

// fn encode_outgoing(message: &OutgoingMessage) -> Option<Message> {
//     if BINARY_OUTBOUND_ACTIONS.contains(&message.action.as_str()) {
//         match rmp_serde::to_vec_named(message) {
//             Ok(bytes) => Some(Message::Binary(bytes.into())),
//             Err(err) => {
//                 println!("failed to encode msgpack action={}: {}", message.action, err);
//                 None
//             }
//         }
//     } else {
//         match serde_json::to_string(message) {
//             Ok(s) => Some(Message::Text(s.into())),
//             Err(err) => {
//                 println!("failed to encode json action={}: {}", message.action, err);
//                 None
//             }
//         }
//     }
// }

// // =====================================================================
// // Internal HTTP routes — Django pushes server-initiated socket traffic
// // here. Auth: X-Rust-Internal-Secret header must match env secret.
// // =====================================================================

// fn check_internal_auth(state: &AppState, headers: &HeaderMap) -> Result<(), StatusCode> {
//     if state.internal_secret.is_empty() {
//         return Err(StatusCode::UNAUTHORIZED);
//     }
//     let provided = headers
//         .get("X-Rust-Internal-Secret")
//         .and_then(|v| v.to_str().ok())
//         .unwrap_or("");
//     if provided == state.internal_secret {
//         Ok(())
//     } else {
//         Err(StatusCode::UNAUTHORIZED)
//     }
// }

// async fn internal_push_user(
//     State(state): State<AppState>,
//     headers: HeaderMap,
//     Json(body): Json<PushUserBody>,
// ) -> impl IntoResponse {
//     if let Err(code) = check_internal_auth(&state, &headers) {
//         return code.into_response();
//     }

//     let txs: Vec<Tx> = {
//         let clients = state.clients.read().await;
//         clients
//             .values()
//             .filter(|c| c.user_id == body.user_id)
//             .map(|c| c.tx.clone())
//             .collect()
//     };

//     if txs.is_empty() {
//         return (StatusCode::OK, Json(json!({ "delivered": 0 }))).into_response();
//     }

//     let outgoing = OutgoingMessage {
//         action: body.action,
//         data: body.data,
//     };
//     let Some(encoded) = encode_outgoing(&outgoing) else {
//         return StatusCode::INTERNAL_SERVER_ERROR.into_response();
//     };

//     let mut delivered = 0usize;
//     for tx in &txs {
//         if tx.send(encoded.clone()).is_ok() {
//             delivered += 1;
//         }
//     }

//     if body.close_after {
//         for tx in &txs {
//             let _ = tx.send(Message::Close(None));
//         }
//     }

//     (StatusCode::OK, Json(json!({ "delivered": delivered }))).into_response()
// }

// async fn internal_push_room(
//     State(state): State<AppState>,
//     headers: HeaderMap,
//     Json(body): Json<PushRoomBody>,
// ) -> impl IntoResponse {
//     if let Err(code) = check_internal_auth(&state, &headers) {
//         return code.into_response();
//     }

//     let outgoing = OutgoingMessage {
//         action: body.action,
//         data: body.data,
//     };
//     let Some(encoded) = encode_outgoing(&outgoing) else {
//         return StatusCode::INTERNAL_SERVER_ERROR.into_response();
//     };

//     let room_client_ids = {
//         let rooms = state.rooms.read().await;
//         rooms.get(&body.room).cloned()
//     };

//     let Some(room_client_ids) = room_client_ids else {
//         return (StatusCode::OK, Json(json!({ "delivered": 0 }))).into_response();
//     };

//     let clients = state.clients.read().await;
//     let mut delivered = 0usize;
//     for cid in room_client_ids {
//         if let Some(c) = clients.get(&cid) {
//             if Some(c.user_id) == body.exclude_user_id {
//                 continue;
//             }
//             if c.tx.send(encoded.clone()).is_ok() {
//                 delivered += 1;
//             }
//         }
//     }

//     (StatusCode::OK, Json(json!({ "delivered": delivered }))).into_response()
// }

// async fn internal_disconnect_user(
//     State(state): State<AppState>,
//     headers: HeaderMap,
//     Json(body): Json<DisconnectUserBody>,
// ) -> impl IntoResponse {
//     if let Err(code) = check_internal_auth(&state, &headers) {
//         return code.into_response();
//     }

//     let txs: Vec<Tx> = {
//         let clients = state.clients.read().await;
//         clients
//             .values()
//             .filter(|c| c.user_id == body.user_id)
//             .map(|c| c.tx.clone())
//             .collect()
//     };

//     let count = txs.len();
//     for tx in txs {
//         let _ = tx.send(Message::Close(None));
//     }

//     (StatusCode::OK, Json(json!({ "closed": count }))).into_response()
// }




use axum::{
    extract::{
        ws::{Message, WebSocket, WebSocketUpgrade},
        Query, State,
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
    time::Instant,
};
use tokio::sync::{mpsc, RwLock};
use uuid::Uuid;

type UserId = u64;
type ClientId = String;
type RoomName = String;
type Tx = mpsc::UnboundedSender<Message>;

const DJANGO_BASE_URL: &str = "http://127.0.0.1:8000";

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
    rooms: Arc<RwLock<HashMap<RoomName, HashSet<ClientId>>>>,
    http: reqwest::Client,
    internal_secret: String,
}

#[derive(Clone)]
struct Client {
    user_id: UserId,
    tx: Tx,
    friend_id: Option<u64>,
    is_host: bool,
    partner_id: Option<u64>,
    partner_username: Option<String>,
    partner_friend_id: Option<u64>,
    partner_friend_name: Option<String>,
    sesh_friend_id: Option<u64>,
    own_room: RoomName,
    shared_room: RoomName,
    partner_room: Option<RoomName>,
    friend_light_color: Option<String>,
    friend_dark_color: Option<String>,
    gecko_message: Option<String>,
    last_seen: Instant,
}

#[derive(Debug, Deserialize)]
struct WsQuery {
    user_id: Option<UserId>,
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

#[tokio::main]
async fn main() {
    let state = AppState {
        clients: Arc::new(RwLock::new(HashMap::new())),
        rooms: Arc::new(RwLock::new(HashMap::new())),
        http: reqwest::Client::new(),
        internal_secret: std::env::var("RUST_INTERNAL_SECRET").unwrap_or_default(),
    };

    if state.internal_secret.is_empty() {
        println!("WARNING: RUST_INTERNAL_SECRET is empty — internal push routes will reject all calls");
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
    println!("Rust websocket running at http://{}", addr);

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
    Query(query): Query<WsQuery>,
    State(state): State<AppState>,
) -> impl IntoResponse {
    ws.on_upgrade(move |socket| handle_socket(socket, query, state))
}

async fn handle_socket(socket: WebSocket, query: WsQuery, state: AppState) {
    let Some(user_id) = query.user_id else {
        println!("rejecting websocket: missing user_id");
        return;
    };

    evict_existing_user(&state, user_id).await;

    let client_id = Uuid::new_v4().to_string();
    let own_room = format!("gecko_energy_{}", user_id);
    let shared_room = format!("gecko_shared_with_friend_{}", user_id);

    let (mut socket_sender, mut socket_receiver) = socket.split();
    let (tx, mut rx) = mpsc::unbounded_channel::<Message>();

    {
        let mut clients = state.clients.write().await;
        clients.insert(
            client_id.clone(),
            Client {
                user_id,
                tx: tx.clone(),
                friend_id: None,
                is_host: false,
                partner_id: None,
                partner_username: None,
                partner_friend_id: None,
                partner_friend_name: None,
                sesh_friend_id: None,
                own_room: own_room.clone(),
                shared_room: shared_room.clone(),
                partner_room: None,
                friend_light_color: None,
                friend_dark_color: None,
                gecko_message: None,
                last_seen: Instant::now(),
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

    hydrate_live_sesh_context(&state, &client_id, true).await;

    if let Some(client) = get_client(&state, &client_id).await {
        if !client.is_host {
            if let Some(partner_id) = client.partner_id {
                proxy_check_host_link_and_load(&state, &client_id, partner_id).await;
            }
        }
    }

    let send_task = tokio::spawn(async move {
        while let Some(message) = rx.recv().await {
            let is_close = matches!(message, Message::Close(_));
            if socket_sender.send(message).await.is_err() {
                break;
            }
            if is_close {
                break;
            }
        }
    });

    let recv_state = state.clone();
    let recv_client_id = client_id.clone();

    let recv_task = tokio::spawn(async move {
        while let Some(result) = socket_receiver.next().await {
            match result {
                Ok(Message::Text(text)) => {
                    mark_seen(&recv_state, &recv_client_id).await;
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
                    mark_seen(&recv_state, &recv_client_id).await;
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
                Ok(Message::Ping(_)) | Ok(Message::Pong(_)) => {
                    mark_seen(&recv_state, &recv_client_id).await;
                }
                Ok(Message::Close(_)) => break,
                Err(err) => {
                    println!("websocket error client_id={} err={}", recv_client_id, err);
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
        "join_live_sesh" => handle_join_live_sesh(state, client_id).await,
        "leave_live_sesh" => handle_leave_live_sesh(state, client_id).await,
        "request_peer_presence" => handle_request_peer_presence(state, client_id).await,

        "get_gecko_message" => handle_get_gecko_message(state, client_id).await,
        "send_front_end_text_to_gecko" => {
            handle_send_front_end_text_to_gecko(state, client_id, data).await
        }
        "send_read_status_to_gecko" => {
            handle_send_read_status_to_gecko(state, client_id, data).await
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

async fn handle_join_live_sesh(state: &AppState, client_id: &str) {
    hydrate_live_sesh_context(state, client_id, false).await;

    let client = get_client(state, client_id).await;
    let Some(client) = client else { return };

    let Some(partner_id) = client.partner_id else {
        send_to_client(
            state,
            client_id,
            OutgoingMessage {
                action: "join_live_sesh_failed".to_string(),
                data: json!({ "reason": "no_active_sesh" }),
            },
        )
        .await;
        return;
    };

    send_to_client(
        state,
        client_id,
        OutgoingMessage {
            action: "join_live_sesh_ok".to_string(),
            data: json!({
                "partner_id": partner_id,
                "partner_username": client.partner_username,
                "partner_friend_id": client.partner_friend_id,
                "partner_friend_name": client.partner_friend_name,
            }),
        },
    )
    .await;

    broadcast_to_room(
        state,
        &client.shared_room,
        Some(client.user_id),
        OutgoingMessage {
            action: "peer_presence".to_string(),
            data: json!({
                "user_id": client.user_id,
                "online": true,
                "friend_light_color": client.friend_light_color,
                "friend_dark_color": client.friend_dark_color,
            }),
        },
    )
    .await;

    if !client.is_host {
        proxy_check_host_link_and_load(state, client_id, partner_id).await;
    }
}

async fn handle_leave_live_sesh(state: &AppState, client_id: &str) {
    let client = get_client(state, client_id).await;
    let Some(client) = client else { return };

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

    let Some(partner_room) = client.partner_room.clone() else {
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

    broadcast_to_room(
        state,
        &partner_room,
        Some(client.user_id),
        OutgoingMessage {
            action: "peer_presence_request".to_string(),
            data: json!({
                "requester_user_id": client.user_id,
            }),
        },
    )
    .await;
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

    {
        let mut clients = state.clients.write().await;
        if let Some(client) = clients.get_mut(client_id) {
            client.gecko_message = message.clone();
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
            }),
        },
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

    let message = match code {
        Some(0) => "Hi! I'm going to start reading this, if ya don't mind!",
        Some(1) => "Still have some to read...",
        Some(2) => "Read em all!",
        _ => "Hrrrrrmmm hmmmmmmmm",
    }
    .to_string();

    handle_send_front_end_text_to_gecko(state, client_id, Some(json!({ "message": message }))).await;
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
    let client = get_client(state, client_id).await;
    let Some(client) = client else { return };

    if client.friend_id.is_none() {
        return;
    }

    let payload = data.unwrap_or_else(|| json!({}));
    let position = payload.get("position").cloned().unwrap_or_else(|| json!([0, 0]));

    broadcast_to_room(
        state,
        &client.shared_room,
        Some(client.user_id),
        OutgoingMessage {
            action: "gecko_coords".to_string(),
            data: json!({
                "from_user": client.user_id,
                "friend_id": client.friend_id,
                "position": position,
            }),
        },
    )
    .await;
}

async fn handle_update_host_gecko_position(
    state: &AppState,
    client_id: &str,
    data: Option<Value>,
) {
    let client = get_client(state, client_id).await;
    let Some(client) = client else { return };

    if !client.is_host || client.friend_id.is_none() {
        return;
    }

    let payload = data.unwrap_or_else(|| json!({}));

    broadcast_to_room(
        state,
        &client.shared_room,
        Some(client.user_id),
        OutgoingMessage {
            action: "host_gecko_coords".to_string(),
            data: json!({
                "from_user": client.user_id,
                "friend_id": client.friend_id,
                "position": payload.get("position").cloned().unwrap_or_else(|| json!([0, 0])),
                "steps": payload.get("steps").cloned().unwrap_or_else(|| json!([])),
                "steps_len": payload.get("steps_len").cloned(),
                "first_fingers": payload.get("first_fingers").cloned().unwrap_or_else(|| json!([])),
                "held_moments": payload.get("held_moments").cloned().unwrap_or_else(|| json!([])),
                "held_moments_len": payload.get("held_moments_len").cloned(),
                "moments": payload.get("moments").cloned().unwrap_or_else(|| json!([])),
                "moments_len": payload.get("moments_len").cloned(),
                "timestamp": payload.get("timestamp").cloned(),
            }),
        },
    )
    .await;
}

async fn handle_update_guest_gecko_position(
    state: &AppState,
    client_id: &str,
    data: Option<Value>,
) {
    let client = get_client(state, client_id).await;
    let Some(client) = client else { return };

    if client.is_host {
        return;
    }

    let payload = data.unwrap_or_else(|| json!({}));

    broadcast_to_room(
        state,
        &client.shared_room,
        Some(client.user_id),
        OutgoingMessage {
            action: "guest_gecko_coords".to_string(),
            data: json!({
                "from_user": client.user_id,
                "position": payload.get("position").cloned().unwrap_or_else(|| json!([0, 0])),
                "steps": payload.get("steps").cloned().unwrap_or_else(|| json!([])),
                "timestamp": payload.get("timestamp").cloned(),
            }),
        },
    )
    .await;
}

async fn handle_update_capsule_progress(
    state: &AppState,
    client_id: &str,
    data: Option<Value>,
) {
    let client = get_client(state, client_id).await;
    let Some(client) = client else { return };

    let payload = data.unwrap_or_else(|| json!({}));
    let capsule_id = payload.get("capsule_id").cloned();
    let new_progress_raw = payload.get("new_progress").cloned();

    let Some(capsule_id) = capsule_id else { return };
    let Some(new_progress_raw) = new_progress_raw else { return };

    let new_progress = new_progress_raw.as_f64().map(|n| n as i64);
    let Some(new_progress) = new_progress else { return };

    broadcast_to_room(
        state,
        &client.shared_room,
        Some(client.user_id),
        OutgoingMessage {
            action: "capsule_progress".to_string(),
            data: json!({
                "from_user": client.user_id,
                "capsule_id": capsule_id,
                "new_progress": new_progress,
                "timestamp": payload.get("timestamp").cloned(),
            }),
        },
    )
    .await;
}

async fn handle_send_all_host_capsules(
    state: &AppState,
    client_id: &str,
    data: Option<Value>,
) {
    let client = get_client(state, client_id).await;
    let Some(client) = client else { return };

    if !client.is_host || client.friend_id.is_none() {
        return;
    }

    let payload = data.unwrap_or_else(|| json!({}));

    broadcast_to_room(
        state,
        &client.shared_room,
        Some(client.user_id),
        OutgoingMessage {
            action: "all_host_capsules".to_string(),
            data: json!({
                "from_user": client.user_id,
                "friend_id": client.friend_id,
                "moments": payload.get("moments").cloned().unwrap_or_else(|| json!([])),
                "moments_len": payload.get("moments_len").cloned(),
                "timestamp": payload.get("timestamp").cloned(),
            }),
        },
    )
    .await;
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
        DJANGO_BASE_URL
    );

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

async fn proxy_action_to_django(
    state: &AppState,
    client_id: &str,
    action: &str,
    data: Option<Value>,
) {
    let client = get_client(state, client_id).await;
    let Some(client) = client else { return };

    let url = format!("{}/users/internal/gecko/socket-action/", DJANGO_BASE_URL);

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

    let response = state
        .http
        .post(url)
        .header("X-Rust-Internal-Secret", &state.internal_secret)
        .json(&json!({
            "user_id": client.user_id,
            "action": action,
            "data": Value::Object(data_with_ctx),
        }))
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

    let parsed: Result<Value, _> = response.json().await;

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

async fn hydrate_live_sesh_context(
    state: &AppState,
    client_id: &str,
    send_initial_score_state: bool,
) {
    let client = get_client(state, client_id).await;
    let Some(client) = client else { return };

    let url = format!(
        "{}/users/internal/gecko/live-sesh-context/?user_id={}",
        DJANGO_BASE_URL, client.user_id
    );

    let response = state
        .http
        .get(url)
        .header("X-Rust-Internal-Secret", &state.internal_secret)
        .send()
        .await;

    let Ok(response) = response else {
        println!(
            "[hydrate_live_sesh_context] django_unreachable user_id={}",
            client.user_id
        );
        return;
    };

    let parsed: Result<Value, _> = response.json().await;
    let Ok(value) = parsed else {
        println!(
            "[hydrate_live_sesh_context] bad_django_response user_id={}",
            client.user_id
        );
        return;
    };

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

    let partner_room = partner_id.map(|pid| format!("gecko_shared_with_friend_{}", pid));

    {
        let mut clients = state.clients.write().await;
        if let Some(c) = clients.get_mut(client_id) {
            c.partner_id = partner_id;
            c.is_host = is_host;
            c.friend_id = friend_id;
            c.sesh_friend_id = sesh_friend_id;
            c.friend_light_color = friend_light_color;
            c.friend_dark_color = friend_dark_color;
            c.partner_username = partner_username;
            c.partner_friend_id = partner_friend_id;
            c.partner_friend_name = partner_friend_name;
            c.partner_room = partner_room.clone();
        }
    }

    if let Some(room) = &partner_room {
        join_room(state, room, client_id).await;
    }

    println!(
        "[hydrate_live_sesh_context] user={} partner_id={:?} is_host={} friend_id={:?} partner_room={:?}",
        client.user_id,
        partner_id,
        is_host,
        friend_id,
        partner_room
    );

    if send_initial_score_state {
        if let Some(score_state) = value.get("score_state").cloned() {
            send_to_client(
                state,
                client_id,
                OutgoingMessage {
                    action: "score_state".to_string(),
                    data: score_state,
                },
            )
            .await;
        }
    }
}

async fn disconnect_cleanup(state: &AppState, client_id: &str) {
    let client = get_client(state, client_id).await;

    if let Some(client) = client {
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
        for set in rooms.values_mut() {
            set.remove(client_id);
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
            let _ = tx.send(msg);
        }

        let _ = tx.send(Message::Close(None));
        println!("evicting older socket for user_id={} client_id={}", user_id, cid);
    }
}

async fn mark_seen(state: &AppState, client_id: &str) {
    let mut clients = state.clients.write().await;
    if let Some(client) = clients.get_mut(client_id) {
        client.last_seen = Instant::now();
    }
}

async fn join_room(state: &AppState, room_name: &str, client_id: &str) {
    let mut rooms = state.rooms.write().await;
    rooms
        .entry(room_name.to_string())
        .or_insert_with(HashSet::new)
        .insert(client_id.to_string());
}

async fn leave_room(state: &AppState, room_name: &str, client_id: &str) {
    let mut rooms = state.rooms.write().await;
    if let Some(set) = rooms.get_mut(room_name) {
        set.remove(client_id);
    }
    rooms.retain(|_, set| !set.is_empty());
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
        rooms.get(room_name).cloned()
    };

    let Some(room_client_ids) = room_client_ids else {
        return;
    };

    let clients = state.clients.read().await;

    for room_client_id in room_client_ids {
        if let Some(client) = clients.get(&room_client_id) {
            if Some(client.user_id) == exclude_user_id {
                continue;
            }

            let _ = client.tx.send(encoded.clone());
        }
    }
}

fn send_outgoing(tx: &Tx, message: OutgoingMessage) {
    if let Some(msg) = encode_outgoing(&message) {
        let _ = tx.send(msg);
    }
}

fn encode_outgoing(message: &OutgoingMessage) -> Option<Message> {
    if BINARY_OUTBOUND_ACTIONS.contains(&message.action.as_str()) {
        match rmp_serde::to_vec_named(message) {
            Ok(bytes) => Some(Message::Binary(bytes.into())),
            Err(err) => {
                println!("failed to encode msgpack action={}: {}", message.action, err);
                None
            }
        }
    } else {
        match serde_json::to_string(message) {
            Ok(s) => Some(Message::Text(s.into())),
            Err(err) => {
                println!("failed to encode json action={}: {}", message.action, err);
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
        if tx.send(encoded.clone()).is_ok() {
            delivered += 1;
        }
    }

    if body.close_after {
        for tx in &txs {
            let _ = tx.send(Message::Close(None));
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

    for cid in room_client_ids {
        if let Some(c) = clients.get(&cid) {
            if Some(c.user_id) == body.exclude_user_id {
                continue;
            }

            if c.tx.send(encoded.clone()).is_ok() {
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
        let _ = tx.send(Message::Close(None));
    }

    (StatusCode::OK, Json(json!({ "closed": count }))).into_response()
}