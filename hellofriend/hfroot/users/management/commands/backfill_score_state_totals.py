from django.core.management.base import BaseCommand

from users.models import GeckoCombinedData, GeckoScoreState


class Command(BaseCommand):
    help = "Copy total_steps/distance/duration/total_gecko_points from GeckoCombinedData onto GeckoScoreState."

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Print what would change without writing.",
        )

    def handle(self, *args, **opts):
        dry_run = opts["dry_run"]

        combined_by_user = {
            c.user_id: c for c in GeckoCombinedData.objects.all()
        }

        updated = 0
        missing_score_state = 0
        skipped_unchanged = 0

        score_states = GeckoScoreState.objects.filter(
            user_id__in=combined_by_user.keys()
        )

        for score in score_states:
            combined = combined_by_user.pop(score.user_id, None)
            if combined is None:
                continue

            unchanged = (
                score.total_steps == combined.total_steps
                and score.total_distance == combined.total_distance
                and score.total_duration == combined.total_duration
                and score.total_gecko_points == combined.total_gecko_points
            )
            if unchanged:
                skipped_unchanged += 1
                continue

            if dry_run:
                self.stdout.write(
                    f"[dry-run] user={score.user_id} "
                    f"steps={score.total_steps}->{combined.total_steps} "
                    f"distance={score.total_distance}->{combined.total_distance} "
                    f"duration={score.total_duration}->{combined.total_duration} "
                    f"points={score.total_gecko_points}->{combined.total_gecko_points}"
                )
            else:
                score.total_steps = combined.total_steps
                score.total_distance = combined.total_distance
                score.total_duration = combined.total_duration
                score.total_gecko_points = combined.total_gecko_points
                score.save(update_fields=[
                    "total_steps",
                    "total_distance",
                    "total_duration",
                    "total_gecko_points",
                ])
            updated += 1

        missing_score_state = len(combined_by_user)

        prefix = "[dry-run] " if dry_run else ""
        self.stdout.write(self.style.SUCCESS(
            f"{prefix}updated={updated} unchanged={skipped_unchanged} "
            f"combined_without_score_state={missing_score_state}"
        ))
