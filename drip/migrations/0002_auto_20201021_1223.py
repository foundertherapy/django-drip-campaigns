# Generated by Django 3.0.7 on 2020-10-21 12:23
from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('drip', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='drip',
            name='sms_text',
            field=models.TextField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='drip',
            name='pre_header_text',
            field=models.TextField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='sentdrip',
            name='sms',
            field=models.TextField(default=None),
            preserve_default=False,
        ),
        migrations.AlterField(
            model_name='sentdrip',
            name='user',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='sent_drips', to=getattr(settings, 'DRIP_CAMPAIGN_USER_MODEL', getattr(settings, 'AUTH_USER_MODEL', 'auth.User'))),
        ),
        migrations.AddField(
            model_name='sentdrip',
            name='pre_header',
            field=models.TextField(default=None),
            preserve_default=False,
        ),
    ]
