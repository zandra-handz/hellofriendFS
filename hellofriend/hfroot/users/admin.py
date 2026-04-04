from django.contrib import admin
from . import models

# Register your models here.
admin.site.register(models.BadRainbowzUser)
admin.site.register(models.UserCategory)
admin.site.register(models.UserAddress)
admin.site.register(models.UserSettings)
admin.site.register(models.UserProfile)
admin.site.register(models.PointsLedger)
admin.site.register(models.GeckoPointsLedger)
admin.site.register(models.GeckoCombinedData) 
admin.site.register(models.GeckoCombinedSession)
admin.site.register(models.GeckoConfigs)
admin.site.register(models.GeckoSleepChangeLog)