# Gecko Message Codes — Rust ↔ Front End Contract

This is the cross-repo contract for gecko socket messages. The Rust enums in
`gecko-socket-rust/src/main.rs` are the **source of truth** for the emotion
codes (the compiler rejects duplicate discriminants). This doc mirrors them so
the React Native FE's `unique_emotion_code` handling stays in sync. **If you
change an enum, update this table in the same commit.**

## Two separate number spaces

Don't conflate these — they are unrelated:

- **`message_code`** — the **incoming trigger** the FE sends *to* the backend to
  request a specific canned message. Per-kind, 0-based. This is a fixed
  contract: the backend must keep handling these exact values the same way.
- **`unique_emotion_code`** — the **outgoing emotion code** the backend emits
  *to* the FE on the `gecko_message` event. Globally unique across all kinds, so
  the FE can identify the specific message instance. Sourced from the enums.
- **`emotion`** — a human-readable emotion string emitted alongside the code
  (the gecko's display/animation state).

The fallback (unknown/missing `message_code`) always emits
`unique_emotion_code: 999` (`Filler::Hrrm`).

## `losing_warning`

Handler: `handle_send_losing_warning_to_gecko`

| message_code (in) | message text | emotion | unique_emotion_code (out) | enum variant |
|---|---|---|---|---|
| 0 | Huh? What was that?? | confused | 4 | `LosingWarning::Huh` |
| 1 | They're digging up one of our moments! Gotta do something! | alarmed | 5 | `LosingWarning::Digging` |
| 2 | My man we are losin' the fight here!! They're gonna be able to read it! | panic | 6 | `LosingWarning::Losing` |
| 3 | MOMENT STOLEN! | devastated | 7 | `LosingWarning::Stolen` |
| 4 | Whew! False alarm. No moment taken - we're in the clear. | relieved | 8 | `LosingWarning::FalseAlarm` |
| _ (fallback) | ???? | neutral | 999 | `Filler::Hrrm` |

## `read_status`

Handler: `handle_send_read_status_to_gecko`

| message_code (in) | message text | emotion | unique_emotion_code (out) | enum variant |
|---|---|---|---|---|
| 0 | Hi! I'm going to start reading this, if ya don't mind! | Cheerful | 1 | `ReadStatus::Hi` |
| 1 | Still have some to read... | Concentrating | 2 | `ReadStatus::StillReading` |
| 2 | Read em all! | Proud | 3 | `ReadStatus::AllRead` |
| _ (fallback) | Hrrrrrmmm hmmmmmmmm | neutral | 999 | `Filler::Hrrm` |

## Reserved / allocated emotion code ranges

To keep `unique_emotion_code` globally unique, each kind owns a block. Allocate
new kinds a fresh block rather than reusing numbers.

| Range | Owner |
|---|---|
| 1–3 | `ReadStatus` |
| 4–8 | `LosingWarning` |
| 999 | `Filler` (shared fallback) |

## `gecko_message` event payload (what the FE receives)

```jsonc
{
  "from_user": 123,
  "message": "MOMENT STOLEN!",
  "emotion": "devastated",
  "unique_emotion_code": 7,
  "kind": "losing_warning",
  "ref_id": "...",
  "timestamp": 1730000000000
}
```
