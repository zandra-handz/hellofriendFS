// use axum::{
//     extract::{
//         ws::{Message, WebSocket, WebSocketUpgrade},
//         State,
//     },
//     response::IntoResponse,
//     routing::get,
//     Router,
// };
// use futures_util::{SinkExt, StreamExt};
// use std::{net::SocketAddr, sync::Arc};
// use tokio::sync::broadcast;

// #[derive(Clone)]
// struct AppState {
//     tx: broadcast::Sender<String>,
// }

// #[tokio::main]
// async fn main() {
//     let (tx, _) = broadcast::channel::<String>(100);
//     let state = Arc::new(AppState { tx });

//     let app = Router::new()
//         .route("/", get(root))
//         .route("/ws/gecko-rust-test", get(ws_handler))
//         .route("/ws/gecko-rust-test/", get(ws_handler))
//         .with_state(state);

//     let addr = SocketAddr::from(([127, 0, 0, 1], 4000));
//     println!("Rust server running at http://{}", addr);
//     println!("WebSocket path: ws://{}/ws/gecko-rust-test/", addr);

//     let listener = tokio::net::TcpListener::bind(addr).await.unwrap();
//     axum::serve(listener, app).await.unwrap();
// }

// async fn root() -> &'static str {
//     "rust socket server is running"
// }

// async fn ws_handler(
//     ws: WebSocketUpgrade,
//     State(state): State<Arc<AppState>>,
// ) -> impl IntoResponse {
//     println!("websocket upgrade request received");
//     ws.on_upgrade(move |socket| handle_socket(socket, state))
// }

// async fn handle_socket(socket: WebSocket, state: Arc<AppState>) {
//     println!("websocket connected");

//     let (mut sender, mut receiver) = socket.split();
//     let mut rx = state.tx.subscribe();

//     let send_task = tokio::spawn(async move {
//         while let Ok(msg) = rx.recv().await {
//             if sender.send(Message::Text(msg.into())).await.is_err() {
//                 break;
//             }
//         }
//     });

//     let recv_tx = state.tx.clone();

//     let recv_task = tokio::spawn(async move {
//         while let Some(result) = receiver.next().await {
//             match result {
//                 Ok(Message::Text(text)) => {
//                     println!("received text: {}", text);
//                     let _ = recv_tx.send(text.to_string());
//                 }
//                 Ok(Message::Binary(bytes)) => {
//                     println!("received binary len={}", bytes.len());
//                 }
//                 Ok(Message::Close(_)) => {
//                     println!("client closed");
//                     break;
//                 }
//                 Ok(_) => {}
//                 Err(err) => {
//                     println!("websocket error: {}", err);
//                     break;
//                 }
//             }
//         }
//     });

//     tokio::select! {
//         _ = send_task => {},
//         _ = recv_task => {},
//     }

//     println!("websocket disconnected");
// }












// use axum::{
//     extract::{
//         ws::{Message, WebSocket, WebSocketUpgrade},
//         Query, State,
//     },
//     response::IntoResponse,
//     routing::get,
//     Router,
// };

// use futures_util::{SinkExt, StreamExt};
// use serde::{Deserialize, Serialize};
// use serde_json::{json,Value};
// use std::{
//     collections::{HashMap, HashSet},
//     net::SocketAddr,
//     sync::Arc,
// };
// use tokio::sync::{mpsc, RwLock};
// use uuid::Uuid;

// type UserId = u64;
// type ClientId = String;
// type Tx = mpsc::UnboundedSender<Message>;

// #[derive(Clone)]
// struct AppState {
//     clients: Arc<RwLock<HashMap<ClientId, Client>>>,
//     rooms: Arc<RwLock<HashMap<String, HashSet<ClientId>>>>,
// }

// #[derive(Clone)]
// struct Client {
//     user_id: UserId,
//     tx: Tx,
// }


// #[derive(Debug, Deserialize)]
// struct WsQuery {
//     user_id: Option<UserId>,
// }


// #[derive(Debug, Deserialize)]
// struct IncomingMessage {
//     action: String,
//     data: Option<Value>,
// }


// #[derive(Debug, Serialize)]
// struct OutgoingMessage {
//     action: String,
//     data: Value,
// }


// #[tokio::main]
// async fn main() {
//     let state = AppState {
//         clients: Arc::new(RwLock::new(HashMap::new())),
//         rooms: Arc::new(RwLock::new(HashMap::new())),
//     };

//     let app = Router::new()
//         .route("/", get(root))
//         .route("/ws/gecko-rust-test", get(ws_handler))
//         .route("/ws/gecko-rust-test/", get(ws_handler))
//         .with_state(state);

//         let addr = SocketAddr::from(([127, 0, 0, 1], 4000));

//         println!("Rust server running at http://{}", addr);
//         println!("WebSocket path: ws://{}/ws/gecko-rust-test/?user_id=123", addr);

//         let listener = tokio::net::TcpListener::bind(addr)
//             .await
//             .expect("failed to bind Rust websocket server");

//         axum::serve(listener, app)
//             .await
//             .expect("Rust websocket server crashed");

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
//         println!("rejecting socket: missing user_id");
//         return;
//     };

//     let client_id = Uuid::new_v4().to_string();
//     let room_name = format!("gecko_energy_{}", user_id);

//     println!(
//         "websocket connected user_id={} client_id={} room={}",
//         user_id, client_id, room_name
//     );

//     let (mut socket_sender, mut socket_receiver) = socket.split();
//     let (tx, mut rx) = mpsc::unbounded_channel::<Message>();

//     {
//         let mut clients = state.clients.write().await;
//         clients.insert(
//             client_id.clone(),
//             Client {
//                 user_id,
//                 tx: tx.clone(),
//             },
//         );
//     }

//     join_room(&state, &room_name, &client_id).await;

//     send_json(
//         &tx,
//         OutgoingMessage {
//             action: "rust_connected".to_string(),
//             data: json!({
//                 "user_id": user_id,
//                 "client_id": client_id,
//                 "room": room_name,
//             }),
//         },
//     );

//     let send_task = tokio::spawn(async move {
//         while let Some(message) = rx.recv().await {
//             if socket_sender.send(message).await.is_err() {
//                 break;
//             }
//         }
//     });

//     let recv_state = state.clone();
//     let recv_client_id = client_id.clone();
//     let recv_room_name = room_name.clone();

//     let recv_task = tokio::spawn(async move {
//         while let Some(result) = socket_receiver.next().await {
//             match result {
//                 Ok(Message::Text(text)) => {
//                     handle_text_message(
//                         &recv_state,
//                         &recv_client_id,
//                         user_id,
//                         &recv_room_name,
//                         text.to_string(),
//                     )
//                     .await;
//                 }

//                 Ok(Message::Binary(bytes)) => {
//                     println!(
//                         "received binary user_id={} client_id={} len={}",
//                         user_id,
//                         recv_client_id,
//                         bytes.len()
//                     );
//                 }

//                 Ok(Message::Ping(_)) | Ok(Message::Pong(_)) => {}

//                 Ok(Message::Close(_)) => {
//                     println!("client closed user_id={} client_id={}", user_id, recv_client_id);
//                     break;
//                 }

//                 Err(err) => {
//                     println!(
//                         "websocket error user_id={} client_id={} err={}",
//                         user_id, recv_client_id, err
//                     );
//                     break;
//                 }
//             }
//         }
//     });

//     tokio::select! {
//         _ = send_task => {},
//         _ = recv_task => {},
//     }

//     cleanup_client(&state, &client_id).await;

//     println!(
//         "websocket disconnected user_id={} client_id={}",
//         user_id, client_id
//     );
// }

// async fn handle_text_message(
//     state: &AppState,
//     client_id: &str,
//     user_id: UserId,
//     room_name: &str,
//     text: String,
// ) {
//     let parsed: Result<IncomingMessage, _> = serde_json::from_str(&text);

//     let Ok(message) = parsed else {
//         send_to_client(
//             state,
//             client_id,
//             OutgoingMessage {
//                 action: "rust_error".to_string(),
//                 data: json!({
//                     "reason": "invalid_json",
//                     "raw": text,
//                 }),
//             },
//         )
//         .await;
//         return;
//     };

//     match message.action.as_str() {
//         "ping" => {
//             send_to_client(
//                 state,
//                 client_id,
//                 OutgoingMessage {
//                     action: "pong".to_string(),
//                     data: json!({
//                         "user_id": user_id,
//                     }),
//                 },
//             )
//             .await;
//         }

//         "get_user_context" => {
//             send_to_client(
//                 state,
//                 client_id,
//                 OutgoingMessage {
//                     action: "user_context".to_string(),
//                     data: json!({
//                         "user_id": user_id,
//                         "room": room_name,
//                         "source": "rust_side_test",
//                         "django_connected": false,
//                     }),
//                 },
//             )
//             .await;
//         }

//         "update_gecko_position" => {
//             let payload = message.data.unwrap_or_else(|| json!({}));
//             let position = payload.get("position").cloned().unwrap_or_else(|| json!([0, 0]));

//             broadcast_to_room(
//                 state,
//                 room_name,
//                 Some(client_id),
//                 OutgoingMessage {
//                     action: "gecko_coords".to_string(),
//                     data: json!({
//                         "from_user": user_id,
//                         "position": position,
//                         "source": "rust",
//                     }),
//                 },
//             )
//             .await;
//         }

//         "update_host_gecko_position" => {
//             let payload = message.data.unwrap_or_else(|| json!({}));

//             broadcast_to_room(
//                 state,
//                 room_name,
//                 Some(client_id),
//                 OutgoingMessage {
//                     action: "host_gecko_coords".to_string(),
//                     data: json!({
//                         "from_user": user_id,
//                         "friend_id": payload.get("friend_id").cloned(),
//                         "position": payload.get("position").cloned().unwrap_or_else(|| json!([0, 0])),
//                         "steps": payload.get("steps").cloned().unwrap_or_else(|| json!([])),
//                         "steps_len": payload.get("steps_len").cloned(),
//                         "first_fingers": payload.get("first_fingers").cloned().unwrap_or_else(|| json!([])),
//                         "held_moments": payload.get("held_moments").cloned().unwrap_or_else(|| json!([])),
//                         "held_moments_len": payload.get("held_moments_len").cloned(),
//                         "moments": payload.get("moments").cloned().unwrap_or_else(|| json!([])),
//                         "moments_len": payload.get("moments_len").cloned(),
//                         "timestamp": payload.get("timestamp").cloned(),
//                         "source": "rust",
//                     }),
//                 },
//             )
//             .await;
//         }

//         "update_guest_gecko_position" => {
//             let payload = message.data.unwrap_or_else(|| json!({}));

//             broadcast_to_room(
//                 state,
//                 room_name,
//                 Some(client_id),
//                 OutgoingMessage {
//                     action: "guest_gecko_coords".to_string(),
//                     data: json!({
//                         "from_user": user_id,
//                         "position": payload.get("position").cloned().unwrap_or_else(|| json!([0, 0])),
//                         "steps": payload.get("steps").cloned().unwrap_or_else(|| json!([])),
//                         "timestamp": payload.get("timestamp").cloned(),
//                         "source": "rust",
//                     }),
//                 },
//             )
//             .await;
//         }

//         _ => {
//             send_to_client(
//                 state,
//                 client_id,
//                 OutgoingMessage {
//                     action: "rust_error".to_string(),
//                     data: json!({
//                         "reason": "unknown_action",
//                         "action": message.action,
//                     }),
//                 },
//             )
//             .await;
//         }
//     }
// }

// async fn join_room(state: &AppState, room_name: &str, client_id: &str) {
//     let mut rooms = state.rooms.write().await;

//     rooms
//         .entry(room_name.to_string())
//         .or_insert_with(HashSet::new)
//         .insert(client_id.to_string());
// }

// async fn cleanup_client(state: &AppState, client_id: &str) {
//     {
//         let mut clients = state.clients.write().await;
//         clients.remove(client_id);
//     }

//     {
//         let mut rooms = state.rooms.write().await;

//         for clients_in_room in rooms.values_mut() {
//             clients_in_room.remove(client_id);
//         }

//         rooms.retain(|_, clients_in_room| !clients_in_room.is_empty());
//     }
// }

// async fn send_to_client(state: &AppState, client_id: &str, message: OutgoingMessage) {
//     let clients = state.clients.read().await;

//     if let Some(client) = clients.get(client_id) {
//         send_json(&client.tx, message);
//     }
// }

// async fn broadcast_to_room(
//     state: &AppState,
//     room_name: &str,
//     exclude_client_id: Option<&str>,
//     message: OutgoingMessage,
// ) {
//     let encoded = match serde_json::to_string(&message) {
//         Ok(value) => value,
//         Err(err) => {
//             println!("failed to encode outgoing message: {}", err);
//             return;
//         }
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
//         if exclude_client_id == Some(room_client_id.as_str()) {
//             continue;
//         }

//         if let Some(client) = clients.get(&room_client_id) {
//             let _ = client.tx.send(Message::Text(encoded.clone().into()));
//         }
//     }
// }

// fn send_json(tx: &Tx, message: OutgoingMessage) {
//     match serde_json::to_string(&message) {
//         Ok(encoded) => {
//             let _ = tx.send(Message::Text(encoded.into()));
//         }
//         Err(err) => {
//             println!("failed to encode json: {}", err);
//         }
//     }
// }





use axum::{
    extract::{
        ws::{Message, WebSocket, WebSocketUpgrade},
        Query, State,
    },
    response::IntoResponse,
    routing::get,
    Router,
};
use futures_util::{SinkExt, StreamExt};
use serde::{Deserialize, Serialize};
use serde_json::{json, Value};
use std::{
    collections::{HashMap, HashSet},
    net::SocketAddr,
    sync::Arc,
    time::{Duration, Instant},
};
use tokio::sync::{mpsc, RwLock};
use uuid::Uuid;

type UserId = u64;
type ClientId = String;
type RoomName = String;
type Tx = mpsc::UnboundedSender<Message>;

const DJANGO_BASE_URL: &str = "http://127.0.0.1:8000";

#[derive(Clone)]
struct AppState {
    clients: Arc<RwLock<HashMap<ClientId, Client>>>,
    rooms: Arc<RwLock<HashMap<RoomName, HashSet<ClientId>>>>,
    http: reqwest::Client,
}

#[derive(Clone)]
struct Client {
    user_id: UserId,
    tx: Tx,
    friend_id: Option<u64>,
    is_host: bool,
    partner_id: Option<u64>,
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

#[derive(Debug, Deserialize)]
struct IncomingMessage {
    action: String,
    data: Option<Value>,
}

#[derive(Debug, Serialize)]
struct OutgoingMessage {
    action: String,
    data: Value,
}

#[tokio::main]
async fn main() {
    let state = AppState {
        clients: Arc::new(RwLock::new(HashMap::new())),
        rooms: Arc::new(RwLock::new(HashMap::new())),
        http: reqwest::Client::new(),
    };

    let app = Router::new()
        .route("/", get(root))
        .route("/ws/gecko-rust-test", get(ws_handler))
        .route("/ws/gecko-rust-test/", get(ws_handler))
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

    send_json(
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

    hydrate_live_sesh_context(&state, &client_id).await;

    let send_task = tokio::spawn(async move {
        while let Some(message) = rx.recv().await {
            if socket_sender.send(message).await.is_err() {
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
                    handle_text_message(&recv_state, &recv_client_id, text.to_string()).await;
                }
                Ok(Message::Binary(bytes)) => {
                    mark_seen(&recv_state, &recv_client_id).await;

                    send_to_client(
                        &recv_state,
                        &recv_client_id,
                        OutgoingMessage {
                            action: "rust_error".to_string(),
                            data: json!({
                                "reason": "binary_not_enabled_yet",
                                "bytes_len": bytes.len(),
                            }),
                        },
                    )
                    .await;
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

async fn handle_text_message(state: &AppState, client_id: &str, text: String) {
    let parsed: Result<IncomingMessage, _> = serde_json::from_str(&text);

    let Ok(message) = parsed else {
        send_to_client(
            state,
            client_id,
            OutgoingMessage {
                action: "rust_error".to_string(),
                data: json!({ "reason": "invalid_json", "raw": text }),
            },
        )
        .await;
        return;
    };

    match message.action.as_str() {
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

        "set_friend" => handle_set_friend(state, client_id, message.data).await,
        "join_live_sesh" => handle_join_live_sesh(state, client_id).await,
        "leave_live_sesh" => handle_leave_live_sesh(state, client_id).await,
        "request_peer_presence" => handle_request_peer_presence(state, client_id).await,

        "get_gecko_message" => handle_get_gecko_message(state, client_id).await,
        "send_front_end_text_to_gecko" => {
            handle_send_front_end_text_to_gecko(state, client_id, message.data).await
        }
        "send_read_status_to_gecko" => {
            handle_send_read_status_to_gecko(state, client_id, message.data).await
        }

        "get_gecko_screen_position" => handle_get_gecko_screen_position(state, client_id).await,
        "update_gecko_position" => handle_update_gecko_position(state, client_id, message.data).await,
        "update_host_gecko_position" => {
            handle_update_host_gecko_position(state, client_id, message.data).await
        }
        "update_guest_gecko_position" => {
            handle_update_guest_gecko_position(state, client_id, message.data).await
        }
        "update_capsule_progress" => {
            handle_update_capsule_progress(state, client_id, message.data).await
        }
        "send_all_host_capsules" => handle_send_all_host_capsules(state, client_id, message.data).await,

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
            proxy_action_to_django(state, client_id, &message.action, message.data).await;
        }

        _ => {
            send_to_client(
                state,
                client_id,
                OutgoingMessage {
                    action: "rust_error".to_string(),
                    data: json!({
                        "reason": "unknown_action",
                        "action": message.action,
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
    hydrate_live_sesh_context(state, client_id).await;

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

    let partner_room = format!("gecko_shared_with_friend_{}", partner_id);
    join_room(state, &partner_room, client_id).await;

    {
        let mut clients = state.clients.write().await;
        if let Some(client) = clients.get_mut(client_id) {
            client.partner_room = Some(partner_room.clone());
        }
    }

    send_to_client(
        state,
        client_id,
        OutgoingMessage {
            action: "join_live_sesh_ok".to_string(),
            data: json!({
                "partner_id": partner_id,
                "partner_username": null,
                "partner_friend_id": null,
                "partner_friend_name": null,
            }),
        },
    )
    .await;

    broadcast_to_room(
        state,
        &client.shared_room,
        Some(client_id),
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
}

async fn handle_leave_live_sesh(state: &AppState, client_id: &str) {
    let client = get_client(state, client_id).await;
    let Some(client) = client else { return };

    broadcast_to_room(
        state,
        &client.shared_room,
        Some(client_id),
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
            Some(client_id),
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
            Some(client_id),
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
        if let Some(client) = clients.get_mut(client_id) {
            client.partner_room = None;
            client.is_host = false;
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
        Some(client_id),
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

    handle_send_front_end_text_to_gecko(
        state,
        client_id,
        Some(json!({
            "message": message
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
        Some(client_id),
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
        Some(client_id),
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
        Some(client_id),
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
    let new_progress = payload.get("new_progress").cloned();

    if capsule_id.is_none() || new_progress.is_none() {
        return;
    }

    broadcast_to_room(
        state,
        &client.shared_room,
        Some(client_id),
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
        Some(client_id),
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

async fn proxy_action_to_django(
    state: &AppState,
    client_id: &str,
    action: &str,
    data: Option<Value>,
) {
    let client = get_client(state, client_id).await;
    let Some(client) = client else { return };

    let url = format!("{}/users/internal/gecko/socket-action/", DJANGO_BASE_URL);

    let response = state
        .http
        .post(url)
        .json(&json!({
            "user_id": client.user_id,
            "action": action,
            "data": data.unwrap_or_else(|| json!({})),
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

async fn hydrate_live_sesh_context(state: &AppState, client_id: &str) {
    let client = get_client(state, client_id).await;
    let Some(client) = client else { return };

    let url = format!(
        "{}/internal/gecko/live-sesh-context/?user_id={}",
        DJANGO_BASE_URL, client.user_id
    );

    // let response = state.http.get(url).send().await;
    let response = state
    .http
    .get(url)
    .header("X-Rust-Internal-Secret", std::env::var("RUST_INTERNAL_SECRET").unwrap_or_default())
    .send()
    .await;

    let Ok(response) = response else {
        return;
    };

    let parsed: Result<Value, _> = response.json().await;
    let Ok(value) = parsed else {
        return;
    };

    let partner_id = value.get("partner_id").and_then(|v| v.as_u64());
    let is_host = value
        .get("is_host")
        .and_then(|v| v.as_bool())
        .unwrap_or(false);
    let friend_id = value.get("friend_id").and_then(|v| v.as_u64());

    let friend_light_color = value
        .get("friend_light_color")
        .and_then(|v| v.as_str())
        .map(|s| s.to_string());

    let friend_dark_color = value
        .get("friend_dark_color")
        .and_then(|v| v.as_str())
        .map(|s| s.to_string());

    {
        let mut clients = state.clients.write().await;
        if let Some(client) = clients.get_mut(client_id) {
            client.partner_id = partner_id;
            client.is_host = is_host;
            client.friend_id = friend_id;
            client.friend_light_color = friend_light_color;
            client.friend_dark_color = friend_dark_color;
        }
    }

    if let Some(partner_id) = partner_id {
        let partner_room = format!("gecko_shared_with_friend_{}", partner_id);
        join_room(state, &partner_room, client_id).await;

        let mut clients = state.clients.write().await;
        if let Some(client) = clients.get_mut(client_id) {
            client.partner_room = Some(partner_room);
        }
    }
}

async fn disconnect_cleanup(state: &AppState, client_id: &str) {
    let client = get_client(state, client_id).await;

    if let Some(client) = client {
        broadcast_to_room(
            state,
            &client.shared_room,
            Some(client_id),
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
        send_json(&client.tx, message);
    }
}

async fn broadcast_to_room(
    state: &AppState,
    room_name: &str,
    exclude_client_id: Option<&str>,
    message: OutgoingMessage,
) {
    let encoded = match serde_json::to_string(&message) {
        Ok(value) => value,
        Err(err) => {
            println!("failed to encode outgoing message: {}", err);
            return;
        }
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
        if exclude_client_id == Some(room_client_id.as_str()) {
            continue;
        }

        if let Some(client) = clients.get(&room_client_id) {
            let _ = client.tx.send(Message::Text(encoded.clone().into()));
        }
    }
}

fn send_json(tx: &Tx, message: OutgoingMessage) {
    match serde_json::to_string(&message) {
        Ok(encoded) => {
            let _ = tx.send(Message::Text(encoded.into()));
        }
        Err(err) => {
            println!("failed to encode json: {}", err);
        }
    }
}



//need to add        GET  /internal/gecko/live-sesh-context/?user_id=2
//                 POST /internal/gecko/socket-action/