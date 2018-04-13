from django.forms import ModelForm, SelectDateWidget
from .models import Documents

from datetime import date


class DocumentsForm(ModelForm):
    class Meta:
        model = Documents
        fields = '__all__'
        widgets = {
            'begin_date': SelectDateWidget(years=range(date.today().year - 10,
                                                       date.today().year + 11)),
            'end_date': SelectDateWidget(years=range(date.today().year - 10,
                                                     date.today().year + 11)),
        }
