import json

from django import forms
from django.contrib.auth.models import User
from django.core import exceptions
from django.db import models
from django.utils.translation import ugettext_lazy as _

from aplus.api import api_reverse
from userprofile.models import UserProfile

class PercentField(models.FloatField):
    """
    A float in range 0.0 to 1.0
    """
    def clean(self, value, model_instance):
        value = super(PercentField, self).clean(value, model_instance)
        if value and (value < 0.0 or value > 1.0):
            raise exceptions.ValidationError(
                _("The number must be between 0.0 and 1.0")
            )
        return value


class SearchSelectField(forms.ModelMultipleChoiceField):
    """
    A generic field to 'search-select' widget.
    """
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.widget.attrs["class"] = "search-select-ajax"


class UsersSearchSelectField(SearchSelectField):
    """
    A field to search users from Api.
    """
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.widget.attrs["data-key-parameter-list"] = "full_name,student_id"

    def clean(self, value):
        if not isinstance(value, list):
            raise exceptions.ValidationError(
                _("Invalid input type.")
            )
        # Aplus database has different 'user.id' and 'userprofile.id' values.
        # The fields contain 'Userprofile' objects, while API uses 'user.id'
        # values, so the convertion between them is necessary.
        for key in value:
            if not User.objects.get(id=key):
                raise exceptions.ValidationError(
                    _("{} is not a valid key.").format(key)
                )
        users = User.objects.filter(id__in=value)
        return UserProfile.objects.filter(user__in=users)


class JSONField(models.TextField):
    """
    Stores JSON object in a text field.
    """
    def __init__(self, *args, **kwargs):
        super(JSONField, self).__init__(*args, **kwargs)

    @classmethod
    def parse_json(cls, value):
        if not value:
            return None
        if isinstance(value, str):
            try:
                return json.loads(value)
            except (TypeError, ValueError):
                raise exceptions.ValidationError(_("Enter valid JSON."))
        return value

    @classmethod
    def print_json(cls, value):
        if not value:
            return ""
        if isinstance(value, str):
            return value
        return json.dumps(value)

    def from_db_value(self, value, expression, connection):
        try:
            return JSONField.parse_json(value)
        except (exceptions.ValidationError):
            return None

    def get_prep_value(self, value):
        return JSONField.print_json(value)

    def to_python(self, value):
        return JSONField.parse_json(value)

    def formfield(self, **kwargs):
        defaults = {
            'form_class': JSONFormField,
        }
        defaults.update(kwargs)
        field = super(JSONField, self).formfield(**defaults)
        if not field.help_text:
            field.help_text = _("Enter valid JSON.")
        return field


class JSONFormField(forms.CharField):
    """
    A JSON text area.
    """
    def to_python(self, value):
        return JSONField.parse_json(value)

    def prepare_value(self, value):
        return JSONField.print_json(value)
