# Generated by Django 5.0.3 on 2024-04-14 17:07

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('friends', '0015_pastmeet_delete_all_unshared_capsules'),
    ]

    operations = [
        migrations.AddField(
            model_name='location',
            name='personal_experience_info',
            field=models.CharField(blank=True, max_length=750, null=True),
        ),
    ]
