# Generated by Django 5.1 on 2024-12-13 22:22

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('users', '0010_usersettings_expo_push_token'),
    ]

    operations = [
        migrations.AddField(
            model_name='useraddress',
            name='is_default',
            field=models.BooleanField(default=False),
        ),
    ]
