from django.core.management.base import BaseCommand
from users.models import BadRainbowzUser, UserCategory


class Command(BaseCommand):
    help = "Ensure every user has the default 'Grab bag' UserCategory"

    def handle(self, *args, **kwargs):
        existing_ids = set(
            UserCategory.objects
            .filter(name='Grab bag', is_deletable=False)
            .values_list('user_id', flat=True)
        )
        missing = BadRainbowzUser.objects.exclude(pk__in=existing_ids)

        UserCategory.objects.bulk_create(
            [UserCategory(user=u, name='Grab bag', is_deletable=False) for u in missing],
            batch_size=500,
        )

        self.stdout.write(self.style.SUCCESS(
            f"Created 'Grab bag' UserCategory for {missing.count()} users"
        ))
