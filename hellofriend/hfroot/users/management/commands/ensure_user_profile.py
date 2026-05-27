from django.core.management.base import BaseCommand
from users.models import BadRainbowzUser, UserProfile


class Command(BaseCommand):
    help = 'Ensure every user has a UserProfile row'

    def handle(self, *args, **kwargs):
        existing_ids = set(UserProfile.objects.values_list('user_id', flat=True))
        missing = BadRainbowzUser.objects.exclude(pk__in=existing_ids)

        UserProfile.objects.bulk_create(
            [UserProfile(user=u) for u in missing],
            batch_size=500,
        )

        self.stdout.write(self.style.SUCCESS(
            f'Created UserProfile for {missing.count()} users'
        ))
