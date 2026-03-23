from django.core.management.base import BaseCommand
from friends.models import Friend, GeckoData

class Command(BaseCommand):
    help = 'Creates GeckoData for existing friends that do not have one'

    def handle(self, *args, **kwargs):
        friends_without_gecko = Friend.objects.filter(geckodata__isnull=True)
        count = friends_without_gecko.count()
        
        for friend in friends_without_gecko:
            GeckoData.objects.create(
                friend=friend,
                user=friend.user,
            )
        
        self.stdout.write(self.style.SUCCESS(f'Created GeckoData for {count} friends'))