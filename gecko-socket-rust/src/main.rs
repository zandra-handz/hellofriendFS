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
use serde_json::{json,Value};
use std::{
    collections::{HashMap, HashSet},
    net::SocketAddr,
    sync::Arc,
};
use tokio::sync::{mpsc, RwLock};
use uuid::Uuid;

type UserId = u64;
type ClientId = String;
type Tx = mpsc::UnboundedSender<Message>;

#[derive(Clone)]
struct AppState {
    clients: Arc<RwLock<HashMap<ClientId, Client>>>,
    rooms: Arc<RwLock<HashMap<String, HashSet<ClientId>>>>,
}

#[derive(Clone)]
struct Client {
    user_id: UserId,
    tx: Tx,
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
    };

    let app = Router::new()
        .route("/", get(root))
        .route("/ws/gecko-rust-test", get(ws_handler))
        .route("/ws/gecko-rust-test/", get(ws_handler))
        .with_state(state);

        let addr = SocketAddr::from(([127, 0, 0, 1], 4000));

        println!("Rust server running at http://{}", addr);
        println!("WebSocket path: ws://{}/ws/gecko-rust-test/?user_id=123", addr);

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
        println!("rejecting socket: missing user_id");
        return;
    };

    let client_id = Uuid::new_v4().to_string();
    let room_name = format!("gecko_energy_{}", user_id);

    println!(
        "websocket connected user_id={} client_id={} room={}",
        user_id, client_id, room_name
    );

    let (mut socket_sender, mut socket_receiver) = socket.split();
    let (tx, mut rx) = mpsc::unbounded_channel::<Message>();

    {
        let mut clients = state.clients.write().await;
        clients.insert(
            client_id.clone(),
            Client {
                user_id,
                tx: tx.clone(),
            },
        );
    }

    join_room(&state, &room_name, &client_id).await;

    send_json(
        &tx,
        OutgoingMessage {
            action: "rust_connected".to_string(),
            data: json!({
                "user_id": user_id,
                "client_id": client_id,
                "room": room_name,
            }),
        },
    );

    let send_task = tokio::spawn(async move {
        while let Some(message) = rx.recv().await {
            if socket_sender.send(message).await.is_err() {
                break;
            }
        }
    });

    let recv_state = state.clone();
    let recv_client_id = client_id.clone();
    let recv_room_name = room_name.clone();

    let recv_task = tokio::spawn(async move {
        while let Some(result) = socket_receiver.next().await {
            match result {
                Ok(Message::Text(text)) => {
                    handle_text_message(
                        &recv_state,
                        &recv_client_id,
                        user_id,
                        &recv_room_name,
                        text.to_string(),
                    )
                    .await;
                }

                Ok(Message::Binary(bytes)) => {
                    println!(
                        "received binary user_id={} client_id={} len={}",
                        user_id,
                        recv_client_id,
                        bytes.len()
                    );
                }

                Ok(Message::Ping(_)) | Ok(Message::Pong(_)) => {}

                Ok(Message::Close(_)) => {
                    println!("client closed user_id={} client_id={}", user_id, recv_client_id);
                    break;
                }

                Err(err) => {
                    println!(
                        "websocket error user_id={} client_id={} err={}",
                        user_id, recv_client_id, err
                    );
                    break;
                }
            }
        }
    });

    tokio::select! {
        _ = send_task => {},
        _ = recv_task => {},
    }

    cleanup_client(&state, &client_id).await;

    println!(
        "websocket disconnected user_id={} client_id={}",
        user_id, client_id
    );
}

async fn handle_text_message(
    state: &AppState,
    client_id: &str,
    user_id: UserId,
    room_name: &str,
    text: String,
) {
    let parsed: Result<IncomingMessage, _> = serde_json::from_str(&text);

    let Ok(message) = parsed else {
        send_to_client(
            state,
            client_id,
            OutgoingMessage {
                action: "rust_error".to_string(),
                data: json!({
                    "reason": "invalid_json",
                    "raw": text,
                }),
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
                    data: json!({
                        "user_id": user_id,
                    }),
                },
            )
            .await;
        }

        "get_user_context" => {
            send_to_client(
                state,
                client_id,
                OutgoingMessage {
                    action: "user_context".to_string(),
                    data: json!({
                        "user_id": user_id,
                        "room": room_name,
                        "source": "rust_side_test",
                        "django_connected": false,
                    }),
                },
            )
            .await;
        }

        "update_gecko_position" => {
            let payload = message.data.unwrap_or_else(|| json!({}));
            let position = payload.get("position").cloned().unwrap_or_else(|| json!([0, 0]));

            broadcast_to_room(
                state,
                room_name,
                Some(client_id),
                OutgoingMessage {
                    action: "gecko_coords".to_string(),
                    data: json!({
                        "from_user": user_id,
                        "position": position,
                        "source": "rust",
                    }),
                },
            )
            .await;
        }

        "update_host_gecko_position" => {
            let payload = message.data.unwrap_or_else(|| json!({}));

            broadcast_to_room(
                state,
                room_name,
                Some(client_id),
                OutgoingMessage {
                    action: "host_gecko_coords".to_string(),
                    data: json!({
                        "from_user": user_id,
                        "friend_id": payload.get("friend_id").cloned(),
                        "position": payload.get("position").cloned().unwrap_or_else(|| json!([0, 0])),
                        "steps": payload.get("steps").cloned().unwrap_or_else(|| json!([])),
                        "steps_len": payload.get("steps_len").cloned(),
                        "first_fingers": payload.get("first_fingers").cloned().unwrap_or_else(|| json!([])),
                        "held_moments": payload.get("held_moments").cloned().unwrap_or_else(|| json!([])),
                        "held_moments_len": payload.get("held_moments_len").cloned(),
                        "moments": payload.get("moments").cloned().unwrap_or_else(|| json!([])),
                        "moments_len": payload.get("moments_len").cloned(),
                        "timestamp": payload.get("timestamp").cloned(),
                        "source": "rust",
                    }),
                },
            )
            .await;
        }

        "update_guest_gecko_position" => {
            let payload = message.data.unwrap_or_else(|| json!({}));

            broadcast_to_room(
                state,
                room_name,
                Some(client_id),
                OutgoingMessage {
                    action: "guest_gecko_coords".to_string(),
                    data: json!({
                        "from_user": user_id,
                        "position": payload.get("position").cloned().unwrap_or_else(|| json!([0, 0])),
                        "steps": payload.get("steps").cloned().unwrap_or_else(|| json!([])),
                        "timestamp": payload.get("timestamp").cloned(),
                        "source": "rust",
                    }),
                },
            )
            .await;
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

async fn join_room(state: &AppState, room_name: &str, client_id: &str) {
    let mut rooms = state.rooms.write().await;

    rooms
        .entry(room_name.to_string())
        .or_insert_with(HashSet::new)
        .insert(client_id.to_string());
}

async fn cleanup_client(state: &AppState, client_id: &str) {
    {
        let mut clients = state.clients.write().await;
        clients.remove(client_id);
    }

    {
        let mut rooms = state.rooms.write().await;

        for clients_in_room in rooms.values_mut() {
            clients_in_room.remove(client_id);
        }

        rooms.retain(|_, clients_in_room| !clients_in_room.is_empty());
    }
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