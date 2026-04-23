# GeckoConfigs & GeckoScoreState — usage map

Every place either model is referenced, as of this snapshot. Intended as a pre-merge checklist.

Paths are relative to `hellofriend/`. Line numbers drift — treat them as hints, confirm before editing.

---

## GeckoConfigs

### Model definition
- `hfroot/users/models.py:828` — `class GeckoConfigs(models.Model)`, `related_name='geckoconfigs'`
- `hfroot/users/models.py:863` — `build_default_active_hours()`
- `hfroot/users/models.py:898–935` — `save()` override: computes default `active_hours` on create, syncs **every** mirrored field onto `self.user.geckoscorestate`, then calls `score_state.recompute_energy()`

### Auto-creation on user signup
- `hfroot/users/models.py:168` — `GeckoConfigs.objects.create(user=self)` inside `BadRainbowzUser.save()` (alongside `GeckoScoreState.objects.create(...)` on the line above)

### Views
- `hfroot/users/views.py:583–588` — `GeckoConfigsView(RetrieveUpdateAPIView)` with `get_or_create`
- `hfroot/users/views.py:386–391` — `GeckoScoreStateView.update()` reads `max_score_multiplier`, `max_streak_length_seconds` from `GeckoConfigs` to cap streak requests
- `hfroot/users/views.py:614` — `active_hours_types` choices endpoint (references `ActivityHours.choices`, not the model itself)
- `hfroot/geckoscripts/views.py:22–23` — `_build_welcome_scripts_for_user` reads `personality_type`, `memory_type`, `active_hours_type`, `story_type` to pick welcome scripts

### Serializers
- `hfroot/users/serializers.py:114–141` — `GeckoConfigsSerializer` (fields + read_only_fields + `active_hours_type_label`)
- `hfroot/users/serializers.py:135` — `model = models.GeckoConfigs`
- `hfroot/users/serializers.py:149–226` — `validate()`:
  - Blocks `active_hours`/`active_hours_type` changes unless `geckoscorestate.energy >= 1.0`
  - Builds defaults using `max_active_hours` (line 194–195)
  - Validates `active_hours` list content (range, length vs `max_active_hours`, dedup)

### URL
- `hfroot/users/urls.py:40` — `gecko/configs/` → `GeckoConfigsView`

### Admin
- `hfroot/users/admin.py:14` — `admin.site.register(models.GeckoConfigs)`

### Management command
- `hfroot/users/management/commands/create_gecko_configs.py` — backfill for existing users without a configs row

### Incidental reads from `self.user.geckoconfigs`
- `hfroot/users/models.py:625` — `recompute_energy()` reads `max_duration_till_revival` from `geckoconfigs` (everything else it needs is already mirrored onto `GeckoScoreState`). **This is the one remaining cross-model read at runtime.**

### Docs / changelogs (informational only)
- `ENERGY_SYSTEM.md:36–40, 89–90, 140, 216, 246`
- `recomputeEnergyExample.tsx:34, 36` (FE mirror comments)
- `hfroot/websocket_setup_changelog.txt:18, 21, 24`
- `hfroot/MANAGEMENT_COMMANDS.md:20–24`
- `hfroot/ISSUES_TO_FIX.txt:146`

---

## GeckoScoreState

### Model definition
- `hfroot/users/models.py:582` — `class GeckoScoreState(models.Model)`, `related_name='geckoscorestate'`
- `hfroot/users/models.py:595–606` — mirrored-from-configs block (`personality_type`, `memory_type`, `active_hours_type`, `story_type`, `stamina`, `max_active_hours`, `max_duration_till_revival`, `max_score_multiplier`, `max_streak_length_seconds`, `active_hours`, `gecko_created_on`)
- `hfroot/users/models.py:611` — `recompute_energy()` (authoritative, runs in request/flush context)

### Auto-creation on user signup
- `hfroot/users/models.py:167` — `GeckoScoreState.objects.create(user=self)` in `BadRainbowzUser.save()` (must run **before** `GeckoConfigs.create(...)` on line 168 so the configs-save mirror step can find it)

### Views
- `hfroot/users/views.py:369–425` — `GeckoScoreStateView(RetrieveUpdateAPIView)`: GET runs `recompute_energy()`, PUT/PATCH handles streak activation (reads caps from `GeckoConfigs`, writes multiplier/`expires_at`)
- `hfroot/users/views.py:434–440` — `dev_reset_energy` (superuser-only)
- `hfroot/users/views.py:448–454` — `dev_deplete_energy` (superuser-only)

### Serializers
- `hfroot/users/serializers.py:47–109` — `GeckoScoreStateSerializer`: ships hot fields + **all mirrored config fields** + derived constants (`recharge_per_second`, `streak_fatigue_multiplier`, etc.)
- `hfroot/users/serializers.py:59` — `model = models.GeckoScoreState`
- `hfroot/users/serializers.py:174` — `GeckoConfigsSerializer.validate()` reads `geckoscorestate.energy` for the "fully rested" gate

### Consumer (WebSocket)
- `hfroot/users/consumers.py:1543–1593` — `_load_initial_state()`: `GeckoScoreState.objects.get_or_create`, runs `recompute_energy()`, then builds the in-memory `score_state` dict (copies every mirrored field). Also loads `GeckoCombinedData` and `ScoreRule`.
- `hfroot/users/consumers.py:1595–1635` — `_flush_to_db()`: writes back `multiplier`, `expires_at`, `energy`, `surplus_energy`, `energy_updated_at`, `revives_at` with `update_fields=[...]`
- `hfroot/users/consumers.py:1006–1218` — `_recompute_energy_in_memory()`: pure-python mirror of model's `recompute_energy`, reads `max_active_hours`, `stamina`, `max_duration_till_revival`, multiplier fields from the in-memory dict
- `hfroot/users/consumers.py:1224–1352` — `_handle_update_in_memory()`: reads `multiplier`, `base_multiplier`, `expires_at`, `max_score_multiplier`, `max_streak_length_seconds`, writes `multiplier` and `expires_at` back into the in-memory dict
- `hfroot/users/consumers.py:1493–1537` — `_serialize_score_state()`: serializes the same shape as `GeckoScoreStateSerializer` from the in-memory dict (payload sent to FE on connect and after every update)

### URL
- `hfroot/users/urls.py:41` — `gecko/score-state/` → `GeckoScoreStateView`

### Admin
- `hfroot/users/admin.py:16` — `admin.site.register(models.GeckoScoreState)`

### Management command
- `hfroot/users/management/commands/create_gecko_score_state.py` — backfill for existing users without a score-state row

### Incidental reads via `self.user.geckoscorestate`
- `hfroot/users/models.py:917` — `GeckoConfigs.save()` syncs mirrored fields onto `score_state` (the **only** writer to the mirrored fields on `GeckoScoreState`, outside of migrations/admin)
- `hfroot/users/models.py:1068` — `GeckoCombinedSession.save()` calls `self.user.geckoscorestate.recompute_energy()`
- `hfroot/users/gecko_helpers.py:269` — `process_gecko_data()` reads `multiplier`, `base_multiplier`, `expires_at` when `points_pre_resolved=False`

### Docs / changelogs (informational only)
- `ENERGY_SYSTEM.md:11, 87–88, 121, 123, 150, 162, 191, 195, 215, 232, 236`
- `recomputeEnergyExample.tsx:2, 17`
- `hfroot/websocket_setup_changelog.txt:15, 18, 20, 28`
- `hfroot/MANAGEMENT_COMMANDS.md:34–38`

---

## Migrations touching either model

- `0030_geckoconfigs.py` — initial `GeckoConfigs`
- `0036_geckoconfigs_active_hours_and_more.py`
- `0037_geckosleepchangelog_delete_activehours_and_more.py`
- `0039_geckoconfigs_max_score_multiplier_geckoscorestate.py` — initial `GeckoScoreState`
- `0040_geckoconfigs_max_streak_length_seconds.py`
- `0042_geckoconfigs_stamina_geckoscorestate_energy_and_more.py`
- `0043_geckoconfigs_max_duration_till_revival_and_more.py`
- `0045_geckoscorestate_active_hours_and_more.py` — adds mirrored config fields onto `GeckoScoreState`
- `0046_friendlinkcode_geckoenergysyncsample.py` — depends on 0045

---

## Shared-owner relationships to double-check before merging

- `GeckoSleepChangeLog` (`hfroot/users/models.py:944+`) — currently has config-shape fields (`active_hours_type`, `max_active_hours`, `active_hours`); confirm its FK to `user` rather than to either of these models.
- `GeckoEnergyLog` — referenced from `recompute_energy`; uses `user` + `GeckoCombinedData`, no direct FK to either model.
- `GeckoCombinedData` — fetched alongside `GeckoScoreState` in `_load_initial_state`; separate model, out of scope for this merge but worth noting the consumer already does two `get_or_create` calls side by side.
- `GeckoEnergySyncSample` — telemetry table, stores snapshots, no FK.
- `ScoreRule` (`geckoscripts`) — loaded once per consumer connect, unrelated.

---

## Reality check on "can they drift"

- **Configs → ScoreState mirror**: only driven by `GeckoConfigs.save()`. Any write path that skips `.save()` (bulk updates, raw SQL, admin quick-edits on `GeckoScoreState`, a future signal) leaves them out of sync.
- **ScoreState → Configs**: does not exist. One-way mirror.
- **Read asymmetry**: `recompute_energy` on the **model** reads `max_duration_till_revival` from `GeckoConfigs` directly (models.py:625). The **consumer's** in-memory recompute reads it from the in-memory snapshot of `GeckoScoreState`. Two sources for the same field.
- **Creation order**: `BadRainbowzUser.save()` creates `GeckoScoreState` first, then `GeckoConfigs` — because `GeckoConfigs.save()` needs `score_state` to exist. Flipping that order would raise `RelatedObjectDoesNotExist`.
