# Generated by Django 5.0.3 on 2024-04-03 02:11

import friends.models
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('friends', '0005_updatestracker'),
    ]

    operations = [
        migrations.AlterField(
            model_name='updatestracker',
            name='last_upcoming_update',
            field=models.DateField(verbose_name=friends.models.get_yesterday),
        ),
    ]