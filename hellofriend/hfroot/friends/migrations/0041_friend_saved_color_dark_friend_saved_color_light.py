# Generated by Django 5.1 on 2024-11-03 15:55

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('friends', '0040_friend_theme_color_font_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='friend',
            name='saved_color_dark',
            field=models.CharField(blank=True, help_text='Hex color code for saved dark theme', max_length=7, null=True),
        ),
        migrations.AddField(
            model_name='friend',
            name='saved_color_light',
            field=models.CharField(blank=True, help_text='Hex color code for saved light theme', max_length=7, null=True),
        ),
    ]
