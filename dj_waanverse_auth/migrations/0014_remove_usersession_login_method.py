# Generated by Django 5.1.1 on 2025-03-12 19:33

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('dj_waanverse_auth', '0013_remove_usersession_dj_waanvers_session_75f974_idx_and_more'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='usersession',
            name='login_method',
        ),
    ]
