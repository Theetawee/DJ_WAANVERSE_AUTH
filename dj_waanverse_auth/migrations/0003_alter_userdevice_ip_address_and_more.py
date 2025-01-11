# Generated by Django 5.1.1 on 2025-01-10 10:29

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('dj_waanverse_auth', '0002_userdevice'),
    ]

    operations = [
        migrations.AlterField(
            model_name='userdevice',
            name='ip_address',
            field=models.GenericIPAddressField(blank=True, null=True),
        ),
        migrations.AlterField(
            model_name='userdevice',
            name='user_agent',
            field=models.TextField(blank=True, null=True),
        ),
    ]