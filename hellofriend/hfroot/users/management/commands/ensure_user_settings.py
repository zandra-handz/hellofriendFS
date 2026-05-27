from django.core.management.base import BaseCommand
from users.models import BadRainbowzUser, UserSettings


class Command(BaseCommand):
    help = 'Ensure every user has a UserSettings row'

    def handle(self, *args, **kwargs):
        existing_ids = set(UserSettings.objects.values_list('user_id', flat=True))
        missing = BadRainbowzUser.objects.exclude(pk__in=existing_ids)

        UserSettings.objects.bulk_create(
            [UserSettings(user=u) for u in missing],
            batch_size=500,
        )

        self.stdout.write(self.style.SUCCESS(
            f'Created UserSettings for {missing.count()} users'
        ))
