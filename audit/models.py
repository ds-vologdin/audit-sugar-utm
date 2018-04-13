from django.db import models


# Create your models here.
class QueueLog(models.Model):
    id_asterisk = models.IntegerField(unique=True)
    date_event = models.DateTimeField(null=True)
    callid = models.CharField(max_length=32)
    queuename = models.CharField(max_length=32)
    agent = models.CharField(max_length=32)
    event = models.CharField(max_length=32)
    data1 = models.CharField(max_length=100)
    data2 = models.CharField(max_length=100)
    data3 = models.CharField(max_length=100)
    data4 = models.CharField(max_length=100)
    data5 = models.CharField(max_length=100)


# Данные о попытках дозвониться, на номера из списка пропущенных вызовов
class TpNoAnswered(models.Model):
    id_phonebase = models.IntegerField(unique=True)
    callerid = models.CharField(max_length=30)
    calldate = models.DateTimeField()
    priority = models.IntegerField()
    retry = models.IntegerField()
    last_calldate = models.DateTimeField(null=True)
    done = models.IntegerField()
    dane_calldate = models.DateTimeField(null=True)
