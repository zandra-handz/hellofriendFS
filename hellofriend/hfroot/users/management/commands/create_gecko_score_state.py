# management/commands/create_gecko_score_state.py

from django.core.management.base import BaseCommand
from users.models import BadRainbowzUser, GeckoScoreState

class Command(BaseCommand):
    help = 'Create GeckoScoreState for existing users that do not have one'

    def handle(self, *args, **kwargs):
        created_count = 0

        for user in BadRainbowzUser.objects.all():
            _, created = GeckoScoreState.objects.get_or_create(user=user)
            if created:
                created_count += 1

        self.stdout.write(self.style.SUCCESS(f'Created GeckoScoreState for {created_count} users'))
