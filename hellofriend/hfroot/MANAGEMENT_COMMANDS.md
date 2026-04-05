# Management Commands

All commands are run from `hellofriend/hfroot/` with `python manage.py <command>`.

---

## friends app

### `create_gecko_data`
Backfills `GeckoData` for existing `Friend` rows that don't have one yet. No arguments.

```
python manage.py create_gecko_data
```

---

## users app

### `create_gecko_configs`
Backfills `GeckoConfigs` for existing users that don't have one. No arguments.

```
python manage.py create_gecko_configs
```

### `create_gecko_combined_data`
Backfills `GeckoCombinedData` for existing users that don't have one. No arguments.

```
python manage.py create_gecko_combined_data
```

### `create_gecko_score_state`
Backfills `GeckoScoreState` for existing users that don't have one. No arguments.

```
python manage.py create_gecko_score_state
```

---

## geckoscripts app

### `create_welcome_script`
Creates a `Welcome` script row. All type flags default to `True` (universal); pass `--no-<flag>` to exclude a type.

Required:
- `--label` — short internal label
- `--body` — script text (use `{user_name}` as a placeholder)

Optional exclusion flags (all default on):
`--no-personality-curious`, `--no-personality-scientific`, `--no-personality-brave`,
`--no-memory-amnesiac`, `--no-memory-remembersome`, `--no-memory-remembermany`,
`--no-hours-day`, `--no-hours-night`, `--no-hours-random`,
`--no-story-learner`, `--no-story-nommer`, `--no-story-escaper`

Optional marker flags:
`--experimental`, `--easter-egg`

Basic universal script:
```
python manage.py create_welcome_script --label "default_hi" --body "Hi {user_name}, welcome!"
```

Only for curious personality at night:
```
python manage.py create_welcome_script \
    --label "curious_night_welcome" \
    --body "Hi {user_name}, welcome back!" \
    --no-personality-scientific --no-personality-brave \
    --no-hours-day --no-hours-random
```

### `create_score_rule`
Creates a `ScoreRule` (static point-conversion entry). `(code, version)` must be unique.

Required:
- `--code` — code sent by the front end
- `--points` — integer points awarded

Optional:
- `--label` — human-readable label (default: empty)
- `--version` — rule version (default: `1`)

```
python manage.py create_score_rule --code FEED_GECKO --label "Fed the gecko" --points 10
```

New version of an existing code:
```
python manage.py create_score_rule --code FEED_GECKO --points 15 --version 2
```
