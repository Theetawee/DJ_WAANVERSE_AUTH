# Generated by Django 5.1.1 on 2025-02-23 10:28

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0006_remove_account_unique_phone_number_and_more'),
    ]

    operations = [
        migrations.AlterField(
            model_name='account',
            name='username',
            field=models.CharField(db_index=True, help_text='Required. 10 characters or fewer.', max_length=35, unique=True),
        ),
    ]
