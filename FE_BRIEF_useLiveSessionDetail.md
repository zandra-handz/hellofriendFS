FE brief — build `useLiveSessionDetail` hook
=============================================

Goal
----
Build a React Query hook for fetching the detail view of one live-sesh
session. Pattern should match `useCurrentLiveSesh` / `useLiveSessions`
already in the project.

Backend endpoint
----------------

  GET /friends/<friend_id>/live-sessions/<session_id>/

  Auth: standard (IsAuthenticated; uses the same JWT bearer as all
        other helloFriendApiClient calls).

  URL params:
    - friend_id  : integer (this user's Friend row id, NOT the partner's user id)
    - session_id : UUID string (e.g. "a1b2c3d4-...")

  Query params: none.

  No POST body. Pure GET.

  Responses:
    200 OK    — payload below
    404       — { detail: "session not found for this user/friend" }
                (means: this user has no PastMeet matching that
                friend_id + session_id pair — i.e., they aren't a
                participant or the session_id is wrong)

Response payload shape
----------------------

```typescript
type LiveSessionDetailResponse = {
  session_id: string;                  // UUID

  hello: {
    id: string;                        // PastMeet UUID
    date: string | null;               // ISO date "YYYY-MM-DD" or null
    created_on: string;                // ISO datetime
    type: string;                      // e.g. "gecko game"
    additional_notes: string | null;
  };

  games: Array<{
    log_id: number;                    // UserFriendLiveSeshLog pk
    host_id: number;                   // user id of host
    guest_id: number;                  // user id of guest
    start: string;                     // ISO datetime
    end: string;                       // ISO datetime
    created_on: string;                // ISO datetime

    // One entry per side. Length is typically 2 (host + guest) but
    // can be 0 or 1 if a side hasn't earned any points yet.
    side_points: Array<{
      user_id: number;
      is_me: boolean;                  // pre-computed server-side
      points: number;
      steps: number;
      distance: number;
    }>;

    // This user's GeckoCombinedSession for this game (steps/distance
    // /points from the gecko activity layer). Null if no row exists
    // yet (e.g., game logged but no gecko data flushed).
    my_combined: {
      id: number;
      live_sesh_log_id: number;
      points_earned: number;
      steps: number;
      distance: number;
      started_on: string;              // ISO datetime
      ended_on: string;                // ISO datetime
    } | null;
  }>;

  // Capsule wins this user *received* during the session (this user
  // accepted them; the win is theirs to keep).
  wins_received: Array<GeckoGameWinPayload>;

  // Capsule wins this user *gave away* during the session (partner
  // accepted; for match-flow each finalize produces one of each).
  wins_given: Array<GeckoGameWinPayload>;
};

type GeckoGameWinPayload = {
  id: number;
  user_id: number;                     // the winner's user id
  user_won_from_id: number | null;     // the user it was won from
  friend_id: number | null;            // the winner's Friend row, may be null
  original_capsule_id: string | null;  // source ThoughtCapsulez UUID
  capsule: string;                     // frozen capsule text snapshot
  gecko_game_type: number;             // raw int
  gecko_game_type_label: string;       // frozen label
  won_by_matching: boolean;            // true for match-flow wins
  matched_capsule_id: string | null;   // the other side's capsule (match flow)
  created_on: string;                  // ISO datetime
};
```

Hook contract (match existing conventions)
------------------------------------------

```typescript
// Suggested file: src/hooks/GeckoCalls/useLiveSessionDetail.ts

type Props = {
  friendId: number | null | undefined;
  sessionId: string | null | undefined;
  enabled?: boolean;
};

const useLiveSessionDetail = ({ friendId, sessionId, enabled = true }: Props) => {
  const { data, isLoading, isSuccess, isError, error, refetch } = useQuery({
    queryKey: ["liveSessionDetail", friendId, sessionId],
    queryFn: () => getLiveSessionDetail(friendId!, sessionId!),
    enabled: !!friendId && !!sessionId && enabled,
    staleTime: 30_000,  // see notes
  });

  return {
    session: data,
    hello: data?.hello ?? null,
    games: data?.games ?? [],
    winsReceived: data?.wins_received ?? [],
    winsGiven: data?.wins_given ?? [],
    isLoading,
    isSuccess,
    isError,
    error,
    refetch,
  };
};
```

API call (add to `src/calls/api.ts`)
------------------------------------

```typescript
export const getLiveSessionDetail = async (
  friendId: number,
  sessionId: string,
) => {
  try {
    const response = await helloFriendApiClient.get(
      `/friends/${friendId}/live-sessions/${sessionId}/`,
    );
    return response.data;
  } catch (e: unknown) {
    handleApiError(e, "Error during getLiveSessionDetail");
  }
};
```

Notes / gotchas
---------------

1. **friend_id is the Friend row id, not the partner's user id.** Same
   convention as all other `/friends/<friend_id>/...` endpoints in this
   project. The user already has a Friend row for the partner — pass
   `friend.id`, not the partner's user id.

2. **404 means "not your session."** Treat as a real not-found, not
   an error to retry. If the user navigates to a detail screen with a
   bad session_id, show an empty state, don't loop.

3. **`is_me` is pre-computed.** Don't recompute it client-side. The
   server already filters and tags side_points rows for the requesting
   user, so trust the flag.

4. **`my_combined` can be null.** Means the gecko activity for that
   specific game hasn't synced to the DB yet (it's an eventually-
   consistent layer). UI should handle null gracefully — show points
   from side_points instead, or just say "syncing."

5. **`wins_received` and `wins_given` are both scoped to this session.**
   They are NOT the user's full win history. If you need the full list,
   that's a different endpoint.

6. **Cache invalidation.**
   - On `helloes_updated` notification with this friend_id, you might
     want to invalidate this query (the underlying hello could have
     been updated).
   - On `gecko_win_match_finalized` or `gecko_win_accepted` from the
     gecko websocket, if it corresponds to this session, invalidate to
     pick up new wins.
   - On `live_sesh_ended` for this session, invalidate to pick up
     final stats.

7. **Stale time:** 30s is a reasonable default. The session is "live"
   while it's active (data flowing in), and "frozen" once expired
   (data is final). Could ratchet `staleTime` higher post-expiry.

8. **Sort order:**
   - `games` is sorted by `start` ascending (oldest first).
   - `wins_received` and `wins_given` are sorted by `created_on` descending
     (newest first).
   - `side_points` within each game is unordered — sort client-side if
     you want a deterministic display.

9. **Query budget on the server is 5 queries** with all the filters
   indexed. Don't paginate the detail view — one session has at most
   tens of games and a small number of wins; fetching everything at
   once is correct.

10. **No write endpoints yet.** This is read-only. If you need to
    annotate the hello (add notes, etc.), use the existing
    `HelloDetail` endpoint at `/friends/<friend_id>/helloes/<uuid:pk>/`
    with the `hello.id` returned here.

What to grab from the existing codebase for reference
-----------------------------------------------------

- `src/hooks/GeckoCalls/useCurrentLiveSesh.ts` — query/return-shape pattern
- `src/hooks/GeckoCalls/useLiveSessions.ts` (or whatever the FE consumer
  of `GET /friends/<friend_id>/live-sessions/` is called) — same friend
  scope, useful for query key conventions
- `src/calls/api.ts` — existing `getCurrentLiveSesh` for axios call shape
  and error-handling convention (`handleApiError`)
