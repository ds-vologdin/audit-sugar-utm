# -*- coding: utf-8 -*-
# Generated by Django 1.11.6 on 2018-03-21 12:19
from __future__ import unicode_literals

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('audit', '0005_tpnoanswered'),
    ]

    operations = [
        migrations.RenameField(
            model_name='tpnoanswered',
            old_name='id_phonegts',
            new_name='id_phonebase',
        ),
    ]
