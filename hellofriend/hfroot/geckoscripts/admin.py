from django.contrib import admin 
from . import models

# Register your models here.
admin.site.register(models.Welcome)
admin.site.register(models.ScoreRule)