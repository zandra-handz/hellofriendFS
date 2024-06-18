# Generated by Django 5.0.3 on 2024-06-14 22:37

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('users', '0005_alter_useraddress_address_alter_useraddress_title_and_more'),
    ]

    operations = [
        migrations.RemoveConstraint(
            model_name='useraddress',
            name='unique_user_title',
        ),
        migrations.RemoveConstraint(
            model_name='useraddress',
            name='unique_user_address',
        ),
        migrations.AlterField(
            model_name='useraddress',
            name='user',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='address', to=settings.AUTH_USER_MODEL),
        ),
        migrations.AlterUniqueTogether(
            name='useraddress',
            unique_together={('user', 'address'), ('user', 'title')},
        ),
    ]