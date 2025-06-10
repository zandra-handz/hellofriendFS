from django.db import models
from datetime import date, timedelta


class NextMeetManager(models.Manager):

    # I only left this when i added the user specific in case this was doing something else too
    def expired_dates(self):
        return self.get_queryset().filter(date__lt=date.today())
    
    def user_expired_dates(self, user): 
        return self.filter(user=user, date__lt=date.today())