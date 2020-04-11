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
    A generic field for the AplusSearchSelectAjax jQuery plugin, i.e.,
    a form HTML widget that queries the API and supports selecting multiple
    values from the search results.

    When you use this field in a form class, you should also define the queryset
    for this field and the HTML data attributes for the widget.
    Check the documentation for the Javascript code
    (assets/js/ajax_search_select.js).

    Depending on the usecase and the queryset parameter supplied to the
    __init__ constructor, you may need to override the clean method in
    a subclass of this field class so that the validation accepts necessary
    values. The initial queryset must only include the initially selected
    values so that the rendered HTML form does not include too much data since
    it would slow down the page load. For example, in the past, user fields
    used to include all users from the database in the HTML form.
    """
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.widget.attrs["class"] = "search-select-ajax"


class UsersSearchSelectField(SearchSelectField):
    """
    Search-select field for users.

    Because the API uses only user IDs while many models refer to user profiles
    and user profiles may have different IDs than the corresponding users,
    this field class takes user IDs as input and converts them into profile IDs
    in the validation.
    """
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.widget.attrs["data-key-parameter-list"] = "full_name,student_id,email"

    def clean(self, value):
        if not isinstance(value, list):
            raise exceptions.ValidationError(
                _("Invalid input type.")
            )
        # Convert user IDs to user profile IDs.
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
