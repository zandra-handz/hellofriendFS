# Generated by Django 5.0.3 on 2024-04-07 19:43

import friends.models
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('friends', '0006_alter_updatestracker_last_upcoming_update'),
    ]

    operations = [
        migrations.AddField(
            model_name='pastmeet',
            name='typed_location',
            field=models.CharField(blank=True, max_length=50, null=True),
        ),
        migrations.AlterField(
            model_name='pastmeet',
            name='thought_capsules_shared',
            field=models.JSONField(blank=True, default=dict, null=True),
        ),
        migrations.AlterField(
            model_name='updatestracker',
            name='last_upcoming_update',
            field=models.DateField(default=friends.models.get_yesterday),
        ),
    ]