from django.contrib import admin
from . import models

# Register your models here.
admin.site.register(models.Category)
admin.site.register(models.Friend)
admin.site.register(models.FriendSuggestionSettings)
admin.site.register(models.FriendFaves)
admin.site.register(models.Image)
admin.site.register(models.Location)
admin.site.register(models.NextMeet)
admin.site.register(models.PastMeet)
admin.site.register(models.ThoughtCapsulez)
admin.site.register(models.UpdatesTracker)