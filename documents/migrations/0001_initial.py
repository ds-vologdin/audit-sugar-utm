# -*- coding: utf-8 -*-
# Generated by Django 1.11.4 on 2017-08-31 13:06
from __future__ import unicode_literals

import datetime
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    initial = True

    dependencies = [
    ]

    operations = [
        migrations.CreateModel(
            name='Company',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=200)),
                ('description', models.TextField(blank=True)),
            ],
        ),
        migrations.CreateModel(
            name='Documents',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=200)),
                ('description', models.TextField(blank=True)),
                ('begin_date', models.DateField()),
                ('end_date', models.DateField(blank=True)),
                ('pub_date', models.DateTimeField(verbose_name='date published')),
                ('file_name', models.FileField(upload_to='documents')),
                ('company', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='documents.Company')),
            ],
        ),
        migrations.CreateModel(
            name='Notify',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=200)),
                ('description', models.TextField(blank=True)),
                ('duration', models.DurationField(default=datetime.timedelta(210))),
                ('replay', models.BooleanField(default=True)),
                ('replay_day', models.DurationField(default=datetime.timedelta(7))),
                ('send_email', models.BooleanField(default=True)),
                ('send_sms', models.BooleanField(default=False)),
            ],
        ),
        migrations.CreateModel(
            name='Type_doc',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=200)),
                ('description', models.TextField(blank=True)),
            ],
        ),
        migrations.CreateModel(
            name='User_contact',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=200)),
                ('description', models.TextField(blank=True)),
                ('email', models.EmailField(blank=True, max_length=254)),
                ('phone', models.CharField(blank=True, max_length=11)),
            ],
        ),
        migrations.AddField(
            model_name='notify',
            name='user_contact',
            field=models.ManyToManyField(to='documents.User_contact'),
        ),
        migrations.AddField(
            model_name='documents',
            name='notify',
            field=models.ManyToManyField(to='documents.Notify'),
        ),
        migrations.AddField(
            model_name='documents',
            name='type_doc',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='documents.Type_doc'),
        ),
    ]
