# Generated by Django 5.0.3 on 2024-04-30 21:47

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('friends', '0018_alter_location_address'),
    ]

    operations = [
        migrations.AlterField(
            model_name='location',
            name='address',
            field=models.CharField(blank=True, max_length=64, null=True, unique=True),
        ),
    ]
