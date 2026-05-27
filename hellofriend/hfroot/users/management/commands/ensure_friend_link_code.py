from django.core.management.base import BaseCommand
from django.utils import timezone
from users.models import BadRainbowzUser, FriendLinkCode


class Command(BaseCommand):
    help = 'Ensure every user has a FriendLinkCode row'

    def handle(self, *args, **kwargs):
        existing_ids = set(FriendLinkCode.objects.values_list('user_id', flat=True))
        missing = BadRainbowzUser.objects.exclude(pk__in=existing_ids)

        # Code must be unique per row, so generate per user. bulk_create would
        # need a uniqueness retry loop on collisions — single-row creates keep
        # this simple. Count is small (one-off backfill).
        now = timezone.now()
        created_count = 0
        for user in missing:
            FriendLinkCode.objects.create(
                user=user,
                code=FriendLinkCode.generate_code(),
                expires_at=now,
            )
            created_count += 1

        self.stdout.write(self.style.SUCCESS(
            f'Created FriendLinkCode for {created_count} users'
        ))
