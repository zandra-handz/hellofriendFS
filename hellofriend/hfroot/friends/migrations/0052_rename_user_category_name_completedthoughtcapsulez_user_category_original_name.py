# Generated by Django 5.1 on 2025-07-04 21:00

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('friends', '0051_completedthoughtcapsulez'),
    ]

    operations = [
        migrations.RenameField(
            model_name='completedthoughtcapsulez',
            old_name='user_category_name',
            new_name='user_category_original_name',
        ),
    ]
