from django.db import models

# Create your models here.
from datetime import timedelta, date


class Company(models.Model):
    name = models.CharField(max_length=200)
    description = models.TextField(blank=True)

    def __str__(self):
        return self.name


class Type_doc(models.Model):
    name = models.CharField(max_length=200)
    description = models.TextField(blank=True)

    def __str__(self):
        return self.name


class User_contact(models.Model):
    name = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    email = models.EmailField(blank=True)
    phone = models.CharField(max_length=12, blank=True)

    def __str__(self):
        return self.name


class Notify(models.Model):
    name = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    duration = models.DurationField(default=timedelta(days=210))
    replay = models.BooleanField(default=True)
    replay_day = models.DurationField(default=timedelta(days=7))
    send_email = models.BooleanField(default=True)
    send_sms = models.BooleanField(default=False)
    user_contact = models.ManyToManyField(User_contact)

    def __str__(self):
        return self.name


class Documents(models.Model):
    name = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    begin_date = models.DateField()
    end_date = models.DateField(blank=True, null=True)
    pub_date = models.DateTimeField('date published')
    file_name = models.FileField(upload_to='documents/files')
    active = models.BooleanField(default=True)
    company = models.ForeignKey(Company, on_delete=models.CASCADE)
    type_doc = models.ForeignKey(Type_doc, on_delete=models.CASCADE)
    notify = models.ManyToManyField(Notify, blank=True)

    def __str__(self):
        return self.name

    def info(self):
        return '%s;%s;%s;%s;%s;%s' % (self.name, self.description,
                                      self.begin_date, self.end_date,
                                      self.pub_date, self.file_name)

    def days_left(self):
        if self.end_date:
            return (self.end_date - date.today()).days
        else:
            return None


class Notify_log(models.Model):
    log = models.CharField(max_length=200)
    datetime_log = models.DateTimeField()
    notify = models.ForeignKey(Notify, blank=True, null=True,
                               on_delete=models.SET_NULL)
    documents = models.ForeignKey(Documents, blank=True, null=True,
                                  on_delete=models.SET_NULL)
    user = models.ForeignKey(User_contact, blank=True, null=True,
                             on_delete=models.SET_NULL)

    def __str__(self):
        return '%s: %s' % (self.datetime_log, self.log)
