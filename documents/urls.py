from django.conf.urls import url

from . import views

app_name = 'documents'

urlpatterns = [
    # ex. /documents/
    url(r'^$', views.index, name='index'),
    # ex. /documents/all/
    url(r'^all/$', views.doc_all, name='doc_all'),
    # ex. /documents/add/
    url(r'^add/$', views.doc_add, name='doc_add'),
    # ex. /documents/3/
    url(r'^(?P<id_doc>[0-9]+)/$', views.doc_detail, name='doc_detail'),
    # ex. /documents/3/download/
    url(r'^(?P<id_doc>[0-9]+)/download/$', views.download_doc, name='download_doc'),
    # ex. /documents/3/edit/
    url(r'^(?P<id_doc>[0-9]+)/edit/$', views.doc_edit, name='doc_edit'),
    # ex. /documents/company/
    url(r'^company/$', views.company, name='company'),
    # ex. /documents/company/2/
    url(r'^company/(?P<id_company>[0-9]+)/$', views.company_documents,
        name='company_documents'),
]
