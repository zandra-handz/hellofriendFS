# Generated by Django 5.1 on 2024-09-13 00:51

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('users', '0009_badrainbowzuser_is_test_user'),
    ]

    operations = [
        migrations.AddField(
            model_name='usersettings',
            name='expo_push_token',
            field=models.CharField(blank=True, max_length=255, null=True),
        ),
    ]