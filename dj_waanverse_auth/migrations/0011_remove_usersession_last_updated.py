# Generated by Django 5.1.1 on 2025-01-14 04:03

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('dj_waanverse_auth', '0010_usersession_login_method'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='usersession',
            name='last_updated',
        ),
    ]