from django.contrib import admin
from . import models

# Register your models here.
admin.site.register(models.BadRainbowzUser)
admin.site.register(models.UserCategory)
admin.site.register(models.UserAddress)
admin.site.register(models.UserSettings)
admin.site.register(models.UserProfile)