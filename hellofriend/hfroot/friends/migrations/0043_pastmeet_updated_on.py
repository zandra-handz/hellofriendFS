# Generated by Django 5.1 on 2024-12-24 00:16

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('friends', '0042_friendaddress_is_default'),
    ]

    operations = [
        migrations.AddField(
            model_name='pastmeet',
            name='updated_on',
            field=models.DateTimeField(auto_now=True, null=True),
        ),
    ]
