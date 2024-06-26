# Generated by Django 5.0.3 on 2024-06-14 22:22

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('users', '0004_remove_userprofile_addresses_useraddress'),
    ]

    operations = [
        migrations.AlterField(
            model_name='useraddress',
            name='address',
            field=models.CharField(blank=True, max_length=64, null=True),
        ),
        migrations.AlterField(
            model_name='useraddress',
            name='title',
            field=models.CharField(max_length=64, null=True),
        ),
        migrations.AddConstraint(
            model_name='useraddress',
            constraint=models.UniqueConstraint(fields=('user', 'title'), name='unique_user_title'),
        ),
        migrations.AddConstraint(
            model_name='useraddress',
            constraint=models.UniqueConstraint(fields=('user', 'address'), name='unique_user_address'),
        ),
    ]
