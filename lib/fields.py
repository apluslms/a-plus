import json

from django.core import exceptions
from django.db import models
from django.utils.translation import ugettext_lazy as _


try:
    # If South is used, it requires additional rules for processing
    # custom fields. In this case we add empty inspection rules for the
    # percent field.
    from south.modelsinspector import add_introspection_rules
    add_introspection_rules([], ["^lib\.fields\.PercentField"])
except:
    pass


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


class JSONField(models.TextField):
    """
    Stores JSON object in a text field.
    """
    def __init__(self, *args, **kwargs):
        super(JSONField, self).__init__(*args, **kwargs)

    def to_python(self, value):
        if not value:
            return None
        try:
            return json.loads(value)
        except (TypeError, ValueError):
            raise exceptions.ValidationError(
                _("Enter valid JSON.")
            )

    def get_prep_value(self, value):
        if not value:
            return ""
        if isinstance(value, str):
            return value
        return json.dumps(value)

    def formfield(self, **kwargs):
        print(kwargs)
        defaults = { 'help_text': _("Enter valid JSON.") }
        defaults.update(kwargs)
        return super(JSONField, self).formfield(**defaults)
