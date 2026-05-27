from django.core.management.base import BaseCommand

from users.models import (
    BadRainbowzUser,
    UserProfile,
    UserSettings,
    UserLifetimeTotals,
    GeckoScoreState,
    FriendLinkCode,
    UserCategory,
    GeckoGameWinPending,
)


class Command(BaseCommand):
    help = (
        "Report which users are missing any of the rows that User.save() "
        "is supposed to create. Read-only — does not write anything. "
        "Run the matching ensure_* command (or backfill_user_lifetime_totals) "
        "to fix anything reported."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--verbose",
            action="store_true",
            help="Print the user IDs missing each row, not just the counts.",
        )

    def handle(self, *args, **opts):
        verbose = opts["verbose"]

        all_user_ids = set(BadRainbowzUser.objects.values_list("id", flat=True))
        total_users = len(all_user_ids)

        checks = [
            ("UserProfile",         set(UserProfile.objects.values_list("user_id", flat=True))),
            ("UserSettings",        set(UserSettings.objects.values_list("user_id", flat=True))),
            ("UserLifetimeTotals",  set(UserLifetimeTotals.objects.values_list("user_id", flat=True))),
            ("GeckoScoreState",     set(GeckoScoreState.objects.values_list("user_id", flat=True))),
            ("FriendLinkCode",      set(FriendLinkCode.objects.values_list("user_id", flat=True))),
            ("GeckoGameWinPending", set(GeckoGameWinPending.objects.values_list("user_id", flat=True))),
            (
                "UserCategory(Grab bag)",
                set(
                    UserCategory.objects
                    .filter(name="Grab bag", is_deletable=False)
                    .values_list("user_id", flat=True)
                ),
            ),
        ]

        self.stdout.write(f"Auditing {total_users} users...\n")

        any_missing = False
        for label, present_ids in checks:
            missing = all_user_ids - present_ids
            if missing:
                any_missing = True
                self.stdout.write(self.style.WARNING(
                    f"  {label}: {len(missing)} missing"
                ))
                if verbose:
                    for uid in sorted(missing):
                        self.stdout.write(f"      user_id={uid}")
            else:
                self.stdout.write(self.style.SUCCESS(
                    f"  {label}: OK"
                ))

        if not any_missing:
            self.stdout.write(self.style.SUCCESS(
                "\nAll users have every expected row."
            ))
        else:
            self.stdout.write(self.style.WARNING(
                "\nGaps found. Run the corresponding ensure_* command "
                "(and backfill_user_lifetime_totals for totals values)."
            ))
