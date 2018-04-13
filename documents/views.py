from transliterate import translit

from django.shortcuts import render, get_object_or_404

# Create your views here.
from django.http import HttpResponse, HttpResponseRedirect

import os
from datetime import datetime

from .models import Documents, Notify, User_contact, Type_doc, Company
from .forms import DocumentsForm


def index(request):
    if not request.user.is_authenticated():
        return HttpResponseRedirect('/utmpays/login/')

    document_list = Documents.objects.order_by('end_date')
    company_list = Company.objects.all()
    type_doc_list = Type_doc.objects.all()
    companys = []
    type_docs = []
    actual = 'checked'
    if request.method == "POST":
        # Тип запроса POST. Возможна передача следующих параметров
        # company, type_doc, actual
        post = request.POST
        # Фильтр по компании
        company_ids = []
        if 'company' in post:
            company_ids = post.getlist('company')
            document_list = document_list.filter(company_id__in=company_ids)

        for company in company_list:
            if str(company.id) in company_ids:
                check = 'checked'
            else:
                check = ''
            companys.append({'id': company.id,
                             'name': company.name,
                             'checked': check,})
        # Фильтр по типу документа
        type_doc_ids = []
        if 'type_doc' in post:
            type_doc_ids = post.getlist('type_doc')
            document_list = document_list.filter(type_doc_id__in=type_doc_ids)

        for type_doc in type_doc_list:
            if str(type_doc.id) in type_doc_ids:
                check = 'checked'
            else:
                check = ''
            type_docs.append({'id': type_doc.id,
                             'name': type_doc.name,
                             'checked': check,})

        # Фильтр по актуальности документов
        if 'actual' in post:
            actual_post = post.get('actual')
            if actual_post == 'True':
                actual = 'checked'
                document_list = document_list.filter(active__exact=True)
            else:
                actual = ''
        else:
            actual = ''
    else:
        # Метод GET. Фильтры не установлены.
        document_list = document_list.filter(active__exact=True)
        for company in company_list:
            companys.append({'id': company.id,
                             'name': company.name,
                             'checked': 'checked',})

        for type_doc in type_doc_list:
            type_docs.append({'id': type_doc.id,
                             'name': type_doc.name,
                             'checked': 'checked',})
                             
    context = {'documents': document_list,
               'user': request.user.username,
               'companys': companys,
               'type_docs': type_docs,
               'actual': actual,
               }
    return render(request, 'documents/index.html', context)


def doc_all(request):
    if not request.user.is_authenticated():
        return HttpResponseRedirect('/utmpays/login/')
    document_list = Documents.objects.order_by('end_date')
        
    context = {'documents': document_list,
               'user': request.user.username,
               }
    return render(request, 'documents/index.html', context)


def company_documents(request, id_company):
    if not request.user.is_authenticated():
        return HttpResponseRedirect('/utmpays/login/')
    document_list = Documents.objects.filter(company_id__exact=id_company).order_by('end_date')
    context = {'documents': document_list,
               'user': request.user.username,
               }
    return render(request, 'documents/index.html', context)


def doc_detail(request, id_doc):
    if not request.user.is_authenticated():
        return HttpResponseRedirect('/utmpays/login/')
    document = get_object_or_404(Documents, pk=id_doc)
    context = {'document': document,
               'user': request.user.username,
               }
    return render(request, 'documents/doc_detail.html', context)


def company(request):
    if not request.user.is_authenticated():
        return HttpResponseRedirect('/utmpays/login/')

    company_list = Company.objects.all()
    context = {'companys': company_list,
               'user': request.user.username,
               }
    return render(request, 'documents/company.html', context)


def doc_add(request):
    if not request.user.is_authenticated():
        return HttpResponseRedirect('/utmpays/login/')
    # if this is a POST request we need to process the form data
    if request.method == 'POST':
        # create a form instance and populate it with data from the request:
        form = DocumentsForm(request.POST, request.FILES)
        # check whether it's valid:
        if form.is_valid():
            form.save()
            # process the data in form.cleaned_data as required
            # ...
            # redirect to a new URL:
            return HttpResponseRedirect('/documents/')

    # if a GET (or any other method) we'll create a blank form
    else:
        form = DocumentsForm(initial={'pub_date': datetime.now()})
    return render(request, 'documents/doc_add.html', {'form': form})


def doc_edit(request, id_doc):
    if not request.user.is_authenticated():
        return HttpResponseRedirect('/utmpays/login/')
    # if this is a POST request we need to process the form data
    document = get_object_or_404(Documents, pk=id_doc)
    if request.method == 'POST':
        print('POST')
        # create a form instance and populate it with data from the request:
        form = DocumentsForm(request.POST, request.FILES, instance=document)
        # check whether it's valid:
        if form.is_valid():
            # form.save()
            document = form.save(commit=False)
            document.save()
            # process the data in form.cleaned_data as required
            # ...
            # redirect to a new URL:
            return HttpResponseRedirect('/documents/')

    # if a GET (or any other method) we'll create a blank form
    else:
        form = DocumentsForm(instance=document)

    return render(request, 'documents/doc_add.html', {'form': form})


def download_doc(request, id_doc):
    if not request.user.is_authenticated():
        return HttpResponseRedirect('/utmpays/login/')

    document = get_object_or_404(Documents, pk=id_doc)

    # Берём только название файла, без названия каталога
    name = document.file_name.name.split('/')[-1]
    response = HttpResponse(content_type='application/pdf')
    # Отдаём файл предварительно транлителировав его (иначе ошибки с русскими
    # именами файлов получаем, пока не разобрался с этой бедой)
    response['Content-Disposition'] = 'attachment; filename=\
"%s"' % (translit(name, 'ru', reversed=True))

    response.write(document.file_name.read())

    return response
