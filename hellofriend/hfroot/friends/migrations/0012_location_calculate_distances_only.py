# Generated by Django 5.0.3 on 2024-04-11 00:21

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('friends', '0011_alter_pastmeet_options_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='location',
            name='calculate_distances_only',
            field=models.BooleanField(default=False),
        ),
    ]