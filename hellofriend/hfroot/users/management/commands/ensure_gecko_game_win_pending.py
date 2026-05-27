from django.core.management.base import BaseCommand
from users.models import BadRainbowzUser, GeckoGameWinPending


class Command(BaseCommand):
    help = 'Ensure every user has a GeckoGameWinPending row'

    def handle(self, *args, **kwargs):
        existing_ids = set(GeckoGameWinPending.objects.values_list('user_id', flat=True))
        missing = BadRainbowzUser.objects.exclude(pk__in=existing_ids)

        GeckoGameWinPending.objects.bulk_create(
            [GeckoGameWinPending(user=u) for u in missing],
            batch_size=500,
        )

        self.stdout.write(self.style.SUCCESS(
            f'Created GeckoGameWinPending for {missing.count()} users'
        ))
