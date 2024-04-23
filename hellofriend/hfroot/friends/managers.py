from django.db import models
from datetime import date, timedelta


class NextMeetManager(models.Manager):

    def expired_dates(self):
        return self.get_queryset().filter(date__lt=date.today())