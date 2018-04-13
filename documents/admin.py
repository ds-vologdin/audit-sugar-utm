from django.contrib import admin

# Register your models here.
from .models import Company, Type_doc, User_contact, Notify, Documents

admin.site.register(Company)
admin.site.register(Type_doc)
admin.site.register(User_contact)
admin.site.register(Notify)
admin.site.register(Documents)
