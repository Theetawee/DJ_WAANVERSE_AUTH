# Generated by Django 5.1.1 on 2025-03-09 07:31

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0007_alter_account_username'),
        ('auth', '0012_alter_user_first_name_max_length'),
    ]

    operations = [
        migrations.AlterField(
            model_name='account',
            name='username',
            field=models.CharField(blank=True, db_index=True, help_text='Optional. 35 characters or fewer.', max_length=35, null=True, unique=True),
        ),
        migrations.AddConstraint(
            model_name='account',
            constraint=models.CheckConstraint(condition=models.Q(('username__isnull', False), ('email_address__isnull', False), ('phone_number__isnull', False), _connector='OR'), name='accounts_account_must_have_contact'),
        ),
    ]
