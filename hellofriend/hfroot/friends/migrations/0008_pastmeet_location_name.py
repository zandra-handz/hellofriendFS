# Generated by Django 5.0.3 on 2024-04-08 22:09

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('friends', '0007_pastmeet_typed_location_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='pastmeet',
            name='location_name',
            field=models.CharField(blank=True, max_length=50, null=True),
        ),
    ]
