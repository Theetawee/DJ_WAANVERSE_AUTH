# Generated by Django 5.1.1 on 2025-01-03 19:38

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='VerificationCode',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('email_address', models.EmailField(blank=True, db_index=True, max_length=254, null=True, unique=True, verbose_name='Email Address')),
                ('phone_number', models.CharField(blank=True, db_index=True, max_length=15, null=True, unique=True, verbose_name='Phone Number')),
                ('is_verified', models.BooleanField(default=False, verbose_name='Is Verified')),
                ('code', models.CharField(max_length=255, unique=True, verbose_name='Verification Code')),
                ('created_at', models.DateTimeField(auto_now_add=True, verbose_name='Created At')),
                ('verified_at', models.DateTimeField(blank=True, null=True, verbose_name='Verified At')),
            ],
            options={
                'verbose_name': 'Verification Code',
                'verbose_name_plural': 'Verification Codes',
            },
        ),
        migrations.CreateModel(
            name='MultiFactorAuth',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('activated', models.BooleanField(default=False)),
                ('activated_at', models.DateTimeField(blank=True, null=True)),
                ('recovery_codes', models.JSONField(blank=True, default=list, null=True)),
                ('secret_key', models.CharField(blank=True, max_length=255, null=True)),
                ('last_updated', models.DateTimeField(auto_now=True)),
                ('account', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name='mfa', to=settings.AUTH_USER_MODEL)),
            ],
        ),
    ]
