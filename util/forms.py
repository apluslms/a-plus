from django import forms
from django.utils.safestring import mark_safe

class PlainTextWidget(forms.Widget):
    def render(self, name, value, attrs={}):
        return mark_safe(value) if value is not None else ''
