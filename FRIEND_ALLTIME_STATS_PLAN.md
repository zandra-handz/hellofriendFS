All-time per-friend stats (wins + points) — design notes
==========================================================

Question
--------
How easy is it to expose all-time wins and points scored during a
particular friend's sessions? FE needs to refresh whenever backend
data changes.


The queries themselves are trivial
----------------------------------

Total wins with a friend (all-time):

    GeckoGameWin.objects.filter(user=request.user, friend_id=friend_id).count()

    - One query.
    - GeckoGameWin.friend is FK'd and indexed.
    - Add `session_id__isnull=False` to scope to session-only wins.

Total points / steps / distance attributed to a friend:

    GeckoCombinedSession.objects
        .filter(user=request.user, friend_id=friend_id)
        .aggregate(
            total_points=Sum('points_earned'),
            total_steps=Sum('steps'),
            total_distance=Sum('distance'),
        )

    - One query.
    - Uses existing Index(fields=['user', 'friend']) on GeckoCombinedSession.
    - Add `live_sesh_log__isnull=False` to scope strictly to co-op session
      points (excluding solo gecko activity attributed to the friend).


The real question is refresh strategy
-------------------------------------

What changes these numbers server-side:

  Stat                       Updated by                            Frequency
  --------------------------------------------------------------------------------
  Wins count                 GeckoGameWin.create (in               Rare — per
                             _finalize_locked /                    accepted win
                             _finalize_match_locked)
  --------------------------------------------------------------------------------
  Combined points/steps/     GeckoCombinedSession.create/update    Frequent — every
  distance                   (in gecko_helpers.py:444)             gecko sync tick
                                                                   during a live sesh

Wins: easy. Accept events are user-initiated and infrequent. FE can
invalidate on gecko_win_accepted / gecko_win_match_finalized socket events.

Points: problem. Live-game precision means refetching on every tick.
Wasteful AND unnecessary, because the live scoreboard for the active
session already arrives on the gecko socket (points_awarded with
my_points / partner_points).


Three options
-------------

Option 1: All-time stats are "between-session" stats. (RECOMMENDED)
  - Don't try to keep them mid-game-live.
  - Refresh triggers:
      * on screen focus / mount (React Query default)
      * on live_sesh_ended (session over → final numbers are knowable)
      * on gecko_win_accepted / gecko_win_match_finalized (wins changed)
  - Mid-session: trust the live scoreboard on the active screen.
  - Cheap. Accurate enough for an "all-time" stat. Users don't expect
    all-time counters to tick second-by-second.

Option 2: Push deltas instead of invalidating.
  - Backend fires a `friend_stats_delta` event on each combined-session
    write (or on a debounce). FE applies the delta to cached stats.
  - Pro: most accurate, no refetch.
  - Con: extra socket plumbing, debounce logic, risk of drift if events
    drop.

Option 3: Server-side cached aggregate.
  - Materialize a per-(user, friend) row that gets updated alongside
    GeckoCombinedSession writes.
  - Endpoint reads one row. Fast.
  - Pro: O(1) read, no aggregation.
  - Con: more write-path code, new table, drift risk if write paths are
    missed. Overkill unless high-traffic.


Recommendation
--------------

Option 1. The aggregate query is cheap (indexed), so opportunistic
refetch on the events above is fine. Don't pretend the all-time number
is live.


When ready to build (option 1)
------------------------------

1. New endpoint:

    GET /friends/<friend_id>/sessions/stats/

   Response:

    {
      "wins_count": 12,
      "total_points": 1450,
      "total_steps": 8200,
      "total_distance": 3300
    }

   Optional query params:
    - ?session_only=true → restrict wins to session_id__isnull=False
                           and points to live_sesh_log__isnull=False

2. FE hook:

    useFriendSessionsStats({ friendId })

   - useQuery, key ["friendSessionsStats", friendId]
   - staleTime: e.g. 60_000
   - Invalidate on:
       * registerOnLiveSeshEnded
       * (via gecko WS) gecko_win_accepted, gecko_win_match_finalized
   - Optionally invalidate on screen focus via useFocusEffect.

3. Don't bother invalidating on points_awarded mid-game. Use the live
   scoreboard for that.


Files mentioned
---------------

- hellofriend/hfroot/users/models.py
    GeckoGameWin (line ~1010)            — has friend FK, indexed
    GeckoCombinedSession (line ~1247)    — has user+friend index
- hellofriend/hfroot/users/gecko_helpers.py
    line ~444 — where GeckoCombinedSession is created
- hellofriend/hfroot/users/views.py
    _finalize_locked / _finalize_match_locked — where GeckoGameWin is created
