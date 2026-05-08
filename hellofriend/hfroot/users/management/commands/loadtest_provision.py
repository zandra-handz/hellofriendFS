"""
Provisions/cleans up load-test users + LiveSesh rows for the Rust websocket
load tester. Writes a JWT bundle the Node load tester consumes.

Usage:
    python manage.py loadtest_provision --n 50
    python manage.py loadtest_provision --n 50 --output ../../loadtest/loadtest_users.json
    python manage.py loadtest_provision --cleanup

NOTE: this is a load-test-only helper. It creates real DB rows under usernames
prefixed `loadtest_`. --cleanup deletes ONLY rows whose username starts with
`loadtest_`, so it cannot touch real users.
"""

import json
import time
from pathlib import Path
from datetime import timedelta

import jwt
from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils import timezone

from users.models import BadRainbowzUser, UserFriendCurrentLiveSesh

USERNAME_PREFIX = "loadtest_"
DEFAULT_OUTPUT = Path(settings.BASE_DIR).parent.parent / "loadtest" / "loadtest_users.json"
JWT_TTL_SECONDS = 60 * 60  # 1 hour — long enough for a full test run


def mint_token(user_id: int, secret: str) -> str:
    """Duplicate of users.views.gecko_socket_token mint logic, with longer TTL."""
    now = int(time.time())
    payload = {
        "user_id": user_id,
        "iat": now,
        "exp": now + JWT_TTL_SECONDS,
    }
    return jwt.encode(payload, secret, algorithm="HS256")


class Command(BaseCommand):
    help = "Provision (or clean up) load-test users and LiveSesh pairs for the Rust websocket load tester."

    def add_arguments(self, parser):
        parser.add_argument(
            "--n",
            type=int,
            default=0,
            help="Number of session pairs (=> 2N users). Required unless --cleanup.",
        )
        parser.add_argument(
            "--output",
            type=str,
            default=str(DEFAULT_OUTPUT),
            help=f"Path to write loadtest_users.json (default: {DEFAULT_OUTPUT}).",
        )
        parser.add_argument(
            "--cleanup",
            action="store_true",
            help="Delete every user whose username starts with 'loadtest_' (cascades sesh rows).",
        )

    def handle(self, *args, **opts):
        if opts["cleanup"]:
            self._cleanup()
            return

        n = opts["n"]
        if n <= 0:
            raise CommandError("--n must be > 0 (or pass --cleanup)")

        secret = getattr(settings, "GECKO_WS_JWT_SECRET", "")
        if not secret:
            raise CommandError("GECKO_WS_JWT_SECRET not configured in settings")

        output_path = Path(opts["output"]).resolve()
        output_path.parent.mkdir(parents=True, exist_ok=True)

        pairs = self._provision(n, secret)

        with output_path.open("w") as f:
            json.dump(pairs, f, indent=2)

        self.stdout.write(
            self.style.SUCCESS(
                f"Provisioned {n} pairs ({2 * n} users). Wrote {output_path}"
            )
        )

    @transaction.atomic
    def _provision(self, n: int, secret: str) -> list[dict]:
        """
        BadRainbowzUser.save() auto-creates a UserFriendCurrentLiveSesh with no
        other_user, which then crashes in its own save(). To avoid touching the
        model, we bypass save() entirely with bulk_create, then build the sesh
        rows manually with other_user set. The auxiliary records skipped by
        bulk_create (UserProfile, GeckoScoreState, etc.) are not needed for the
        load-test path; the Rust hydration view tolerates their absence.
        """
        expires_at = timezone.now() + timedelta(hours=2)

        to_create = []
        for i in range(1, n + 1):
            for role in ("host", "guest"):
                username = f"{USERNAME_PREFIX}{role}_{i:04d}"
                u = BadRainbowzUser(
                    username=username,
                    email=f"{username}@loadtest.local",
                    is_test_user=True,
                )
                u.set_unusable_password()
                to_create.append(u)

        BadRainbowzUser.objects.bulk_create(to_create, ignore_conflicts=True)

        usernames = [u.username for u in to_create]
        users = {
            u.username: u
            for u in BadRainbowzUser.objects.filter(username__in=usernames)
        }

        pairs = []
        for i in range(1, n + 1):
            host = users[f"{USERNAME_PREFIX}host_{i:04d}"]
            guest = users[f"{USERNAME_PREFIX}guest_{i:04d}"]

            UserFriendCurrentLiveSesh.objects.update_or_create(
                user=host,
                defaults={
                    "is_host": True,
                    "other_user": guest,
                    "session_start": timezone.now(),
                    "expires_at": expires_at,
                },
            )
            UserFriendCurrentLiveSesh.objects.update_or_create(
                user=guest,
                defaults={
                    "is_host": False,
                    "other_user": host,
                    "session_start": timezone.now(),
                    "expires_at": expires_at,
                },
            )

            pairs.append({
                "host_token": mint_token(host.id, secret),
                "guest_token": mint_token(guest.id, secret),
            })

        return pairs

    @transaction.atomic
    def _cleanup(self):
        qs = BadRainbowzUser.objects.filter(username__startswith=USERNAME_PREFIX)
        count = qs.count()
        qs.delete()
        self.stdout.write(
            self.style.SUCCESS(
                f"Deleted {count} loadtest users (and cascaded sesh rows)."
            )
        )
