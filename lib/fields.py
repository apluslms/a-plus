import json

from django.db import models
from django.core import exceptions
from django.core.serializers.json import DjangoJSONEncoder
from django.utils.translation import ugettext_lazy as _
from django.forms.fields import Field
from django.forms.util import ValidationError as FormValidationError

########################################################################
# Adapted from http://djangosnippets.org/snippets/1914/
########################################################################
class PercentField(models.FloatField):
    """ A field that allows a value between 0 and 1 """

    default_error_messages = {
        'range': 'The number must be between 0.0 and 1.0.',
    }

    def clean(self, value, model_instance):
        """
        Validates that the input can be converted to a value between 0 and 1.
        Returns a float
        """
        value = super(PercentField, self).clean(value, model_instance)
        
        if value is None:
            return None
        
        if (0.0 <= value <= 1.0):
            return value
        
        raise exceptions.ValidationError(self.error_messages['range'])

try:
    # If South is used, it requires additional rules for processing
    # custom fields. In this case we add empty inspection rules for the
    # percentage field.
    from south.modelsinspector import add_introspection_rules
    add_introspection_rules([], ["^lib\.fields\.PercentField"])
except:
    pass

########################################################################
# Django-JSONField by Brad Jasper 
# https://github.com/bradjasper/django-jsonfield
########################################################################
class JSONFormField(Field):
    def clean(self, value):
        if not value and not self.required:
            return None
        
        value = super(JSONFormField, self).clean(value)
        
        try:
            json.loads(value)
        except ValueError:
            raise FormValidationError(_("Enter valid JSON"))
        return value

class JSONField(models.TextField):
    """JSONField is a generic textfield that serializes/unserializes JSON objects"""
    
    # Used so to_python() is called
    __metaclass__ = models.SubfieldBase
    
    def __init__(self, *args, **kwargs):
        self.dump_kwargs = kwargs.pop('dump_kwargs', {'cls': DjangoJSONEncoder})
        self.load_kwargs = kwargs.pop('load_kwargs', {})
        
        super(JSONField, self).__init__(*args, **kwargs)
    
    def to_python(self, value):
        """Convert string value to JSON"""
        if isinstance(value, basestring):
            try:
                return json.loads(value, **self.load_kwargs)
            except ValueError:
                pass
        return value
    
    def get_db_prep_value(self, value, connection, prepared=False):
        """Convert JSON object to a string"""
        
        if isinstance(value, basestring):
            return value
        return json.dumps(value, **self.dump_kwargs)
    
    def value_to_string(self, obj):
        value = self._get_val_from_obj(obj)
        return self.get_prep_value(value)
    
    def value_from_object(self, obj):
        return json.dumps(super(JSONField, self).value_from_object(obj))
    
    def formfield(self, **kwargs):
        if "form_class" not in kwargs:
            kwargs["form_class"] = JSONFormField
        
        field = super(JSONField, self).formfield(**kwargs)
        
        if not field.help_text:
            field.help_text = "Enter valid JSON"
        
        return field

try:
    from south.modelsinspector import add_introspection_rules
    add_introspection_rules([([JSONField], [], {
        "dump_kwargs": ("dump_kwargs", {"default": {'cls': DjangoJSONEncoder}}),
        "load_kwargs": ("load_kwargs", {"default": {}})
    })], ["^lib\.fields\.JSONField"])
except:
    pass
