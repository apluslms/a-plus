from django import forms

class PlainTextWidget(forms.Widget):
    def render(self, name, value, attrs={}):
        return mark_safe(value) if value is not None else ''
