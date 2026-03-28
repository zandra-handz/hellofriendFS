# management/commands/create_gecko_combined_data.py

from django.core.management.base import BaseCommand
from users.models import BadRainbowzUser, GeckoConfigs

class Command(BaseCommand):
    help = 'Create GeckoConfigs for existing users'

    def handle(self, *args, **kwargs):
        users = BadRainbowzUser.objects.filter(geckoconfigs__isnull=True)
        created_count = 0

        for user in users:
            GeckoConfigs.objects.get_or_create(user=user)
            created_count += 1

        self.stdout.write(self.style.SUCCESS(f'Created GeckoConfigs for {created_count} users'))