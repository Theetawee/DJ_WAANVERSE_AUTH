# Generated by Django 5.1.1 on 2025-01-03 10:15

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('dj_waanverse_auth', '0006_remove_emailaddress_user_and_more'),
    ]

    operations = [
        migrations.CreateModel(
            name='VerificationCode',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('email_address', models.EmailField(blank=True, db_index=True, max_length=254, null=True, unique=True)),
                ('phone_number', models.CharField(blank=True, db_index=True, max_length=15, null=True, unique=True)),
                ('is_verified', models.BooleanField(default=False)),
                ('code', models.CharField(max_length=255, unique=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
            ],
        ),
    ]
