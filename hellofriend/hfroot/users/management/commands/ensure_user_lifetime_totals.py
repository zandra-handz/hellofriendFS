from django.core.management.base import BaseCommand
from users.models import BadRainbowzUser, UserLifetimeTotals


class Command(BaseCommand):
    help = 'Ensure every user has a UserLifetimeTotals row'

    def handle(self, *args, **kwargs):
        existing_ids = set(UserLifetimeTotals.objects.values_list('user_id', flat=True))
        missing = BadRainbowzUser.objects.exclude(pk__in=existing_ids)

        UserLifetimeTotals.objects.bulk_create(
            [UserLifetimeTotals(user=u) for u in missing],
            batch_size=500,
        )

        self.stdout.write(self.style.SUCCESS(
            f'Created UserLifetimeTotals for {missing.count()} users'
        ))
