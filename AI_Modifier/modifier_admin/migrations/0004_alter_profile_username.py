# Generated by Django 4.0.5 on 2022-07-05 09:27

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('modifier_admin', '0003_alter_profile_password_alter_profile_username'),
    ]

    operations = [
        migrations.AlterField(
            model_name='profile',
            name='username',
            field=models.CharField(blank=True, max_length=100, null=True),
        ),
    ]
