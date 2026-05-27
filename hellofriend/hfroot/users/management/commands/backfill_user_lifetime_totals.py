from django.core.management.base import BaseCommand

from users.models import GeckoScoreState, UserLifetimeTotals


class Command(BaseCommand):
    help = (
        "Copy total_steps/distance/duration/total_gecko_points from "
        "GeckoScoreState onto UserLifetimeTotals. Creates UserLifetimeTotals "
        "rows for users missing one. Idempotent — safe to re-run."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Print what would change without writing.",
        )

    def handle(self, *args, **opts):
        dry_run = opts["dry_run"]

        score_by_user = {
            s.user_id: s for s in GeckoScoreState.objects.all()
        }

        existing_totals = {
            t.user_id: t for t in UserLifetimeTotals.objects.filter(
                user_id__in=score_by_user.keys()
            )
        }

        updated = 0
        created = 0
        skipped_unchanged = 0
        to_create = []

        for user_id, score in score_by_user.items():
            totals = existing_totals.get(user_id)

            if totals is None:
                if dry_run:
                    self.stdout.write(
                        f"[dry-run] create user={user_id} "
                        f"steps={score.total_steps} distance={score.total_distance} "
                        f"duration={score.total_duration} points={score.total_gecko_points}"
                    )
                else:
                    to_create.append(UserLifetimeTotals(
                        user_id=user_id,
                        total_steps=score.total_steps,
                        total_distance=score.total_distance,
                        total_duration=score.total_duration,
                        total_gecko_points=score.total_gecko_points,
                    ))
                created += 1
                continue

            unchanged = (
                totals.total_steps == score.total_steps
                and totals.total_distance == score.total_distance
                and totals.total_duration == score.total_duration
                and totals.total_gecko_points == score.total_gecko_points
            )
            if unchanged:
                skipped_unchanged += 1
                continue

            if dry_run:
                self.stdout.write(
                    f"[dry-run] user={user_id} "
                    f"steps={totals.total_steps}->{score.total_steps} "
                    f"distance={totals.total_distance}->{score.total_distance} "
                    f"duration={totals.total_duration}->{score.total_duration} "
                    f"points={totals.total_gecko_points}->{score.total_gecko_points}"
                )
            else:
                totals.total_steps = score.total_steps
                totals.total_distance = score.total_distance
                totals.total_duration = score.total_duration
                totals.total_gecko_points = score.total_gecko_points
                totals.save(update_fields=[
                    "total_steps",
                    "total_distance",
                    "total_duration",
                    "total_gecko_points",
                ])
            updated += 1

        if to_create:
            UserLifetimeTotals.objects.bulk_create(to_create, batch_size=500)

        prefix = "[dry-run] " if dry_run else ""
        self.stdout.write(self.style.SUCCESS(
            f"{prefix}created={created} updated={updated} unchanged={skipped_unchanged}"
        ))
