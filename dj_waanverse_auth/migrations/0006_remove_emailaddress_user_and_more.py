# Generated by Django 5.1.1 on 2025-01-03 06:49

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('dj_waanverse_auth', '0005_alter_resetpasswordcode_code'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='emailaddress',
            name='user',
        ),
        migrations.RemoveField(
            model_name='emailconfirmationcode',
            name='user',
        ),
        migrations.DeleteModel(
            name='ResetPasswordCode',
        ),
        migrations.RemoveField(
            model_name='userloginactivity',
            name='account',
        ),
        migrations.DeleteModel(
            name='EmailAddress',
        ),
        migrations.DeleteModel(
            name='EmailConfirmationCode',
        ),
        migrations.DeleteModel(
            name='UserLoginActivity',
        ),
    ]