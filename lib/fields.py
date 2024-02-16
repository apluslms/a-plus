import json
from typing import Any, List, Optional, Tuple

from django import forms
from django.core import exceptions, validators
from django.db import models
from django.db.models.fields import related_descriptors
from django.utils.translation import gettext_lazy as _

from .widgets import DurationInput, SearchSelect


class PercentField(models.FloatField):
    """
    A float in range 0.0 to 1.0
    """
    def clean(self, value, model_instance):
        value = super().clean(value, model_instance)
        if value and (value < 0.0 or value > 1.0):
            raise exceptions.ValidationError(
                _('ERROR_NUMBER_MUST_BE_BETWEEN_0_AND_1')
            )
        return value


class DurationField(forms.MultiValueField):
    """
    A field for entering a duration of time.

    Uses the `lib.widgets.DurationInput` widget, which renders as a row of text
    boxes, one for each given unit of time. The units of time are, by default,
    days, hours and minutes, but they can also be customized by passing a list
    of tuples where the first item is the name of the unit and the second item
    is its factor relative to seconds (e.g. 3600 for hours).
    """
    DAYS = (_('DURATION_UNIT_DAYS'), 60 * 60 * 24)
    HOURS = (_('DURATION_UNIT_HOURS'), 60 * 60)
    MINUTES = (_('DURATION_UNIT_MINUTES'), 60)
    SECONDS = (_('DURATION_UNIT_SECONDS'), 1)

    # Default units
    units: List[Tuple[str, int]] = [DAYS, HOURS, MINUTES, SECONDS]

    def __init__( # pylint: disable=keyword-arg-before-vararg
            self,
            units: List[Tuple[str, int]] = None,
            min_value: Optional[int] = None,
            max_value: Optional[int] = None,
            *args: Any,
            **kwargs: Any,
            ) -> None:
        if units is not None:
            self.units = units
        self.max_value = max_value
        self.min_value = min_value
        fields = [forms.IntegerField() for name, factor in self.units]
        super().__init__(fields, widget=DurationInput(self.units), *args, **kwargs)

        if max_value is not None:
            self.validators.append(validators.MaxValueValidator(max_value))
        if min_value is not None:
            self.validators.append(validators.MinValueValidator(min_value))

    def compress(self, data_list: List[Optional[int]]) -> Optional[int]:
        """
        Convert the values given in different units into seconds.
        """
        total_seconds = None
        for value, (_name, factor) in zip(data_list, self.units):
            if value is None:
                continue
            if total_seconds is None:
                total_seconds = 0
            total_seconds += value * factor
        return total_seconds


class SearchSelectField(forms.ModelMultipleChoiceField):
    """
    A generic form field for the AplusSearchSelectAjax jQuery plugin, i.e.,
    a form HTML widget that queries the API and supports selecting multiple
    values from the search results. The JavaScript code is in the file
    assets/js/ajax_search_select.js.

    This field is mostly the same as the parent class ModelMultipleChoiceField.
    It can be used with ModelForms when the model's ManyToManyField has so
    many values that a normal select-multiple HTML widget would be unusable.
    For example, selecting users from thousands of options would be infeasible
    for the user.

    The constructor has a new argument initial_queryset that is used to render
    choices in the HTML select element instead of using queryset for that.
    Queryset is still used for validating the user input. Initial_queryset is
    used to supply the initial selection to the JavaScript code so that it can
    be rendered on page load. Initial_queryset must not include any other
    choices so that the size of the HTML page does not grow too much.
    This field class and the JS code were designed to be used with user fields
    when the database has thousands of users. Including all users in the options
    of the HTML select element would slow down the page load.

    When you use this field in a form class, you must also define the queryset
    and initial_queryset arguments for this field. They can be set in the form
    constructor if they depend on the form constructor parameters.
    Furthermore, the HTML data attributes for the widget must be set
    (usually in the form constructor). Check the documentation for the Javascript
    code (assets/js/ajax_search_select.js).
    """

    def __init__(
            self,
            queryset: models.QuerySet,
            initial_queryset: models.QuerySet,
            *args: Any,
            **kwargs: Any,
            ) -> None:
        """
        The queryset argument is used for validating the user input.
        The initial_queryset argument is new to this class and it is used
        to render the choices of the HTML select element. It must be set
        to only the initially selected values of the model field, i.e.,
        the old value of the model field so that the form can render the
        initial selection without including massive amounts of data
        (all valid choices) in the HTML page. The initial_queryset does not
        restrict the user's choices since the widget queries the API for new
        choices and the input is validated using queryset, which should be
        "bigger" than initial_queryset.
        """
        if 'widget' not in kwargs:
            kwargs['widget'] = SearchSelect(ajax=True)
        super().__init__(queryset, *args, **kwargs)
        self.initial_queryset = initial_queryset

    def _set_queryset(self, queryset):
        # This method was copied from the super class ModelChoiceField.
        # It is otherwise the same, but we do not modify widget.choices here.
        # widget.choices are controlled by the new initial_queryset variable.
        self._queryset = None if queryset is None else queryset.all()
        # widget.choices must not be based on self.queryset.
        #self.widget.choices = self.choices

    # Override the queryset setter with our version.
    queryset = property(forms.ModelMultipleChoiceField._get_queryset, _set_queryset)

    def _get_initial_queryset(self):
        return self._initial_queryset

    def _set_initial_queryset(self, initial_queryset):
        self._initial_queryset = None if initial_queryset is None else initial_queryset.all()
        # Set the widget's choices to the initial_queryset so that only
        # the initial values are rendered into the select-multiple HTML element.
        # The parent class uses ModelChoiceIterator for setting widget.choices.
        # ModelChoiceIterator uses field.queryset as its queryset, but we can
        # overwrite it after constructing the object.
        choice_iterator = self.iterator(self)
        choice_iterator.queryset = self._initial_queryset
        # The solution for setting widget.choices is copied from the parent class:
        # ModelChoiceField, method _get_choices.
        # https://github.com/django/django/blob/3ab5235d1dc94f7c8fe37a98c4e2c2337a5e5548/django/forms/models.py#L1231
        self.widget.choices = choice_iterator

    initial_queryset = property(_get_initial_queryset, _set_initial_queryset)

    def clean(self, value):
        qs = super().clean(value)
        self.initial_queryset = qs
        return qs


class UsersSearchSelectField(SearchSelectField):
    """
    Search-select field for users.

    Because the API uses only user IDs while many models refer to user profiles
    and user profiles may have different IDs than the corresponding users,
    this field class takes user IDs as input (in the form submission) and
    converts them into profile IDs in the validation. The querysets attached
    to this field must be of type UserProfile, not User, and likewise,
    the corresponding model field must be a ManyToManyField to UserProfile.
    """
    def __init__(self, *args: Any, **kwargs: Any) -> None:
        # to_field_name: use User IDs in the HTML widget since the queryset
        # is attached to UserProfiles.
        # to_field_name affects both the value attributes in the HTML form and
        # the validation of the user's input.
        kwargs['to_field_name'] = 'user_id' # userprofile.user.id
        if 'widget' not in kwargs:
            # Create a search select widget specialized for users.
            kwargs['widget'] = SearchSelect(
                ajax=True,
                display_fields=['full_name', 'student_id', 'email'],
                clipboard_fields=['student_id', 'email'],
                field_sources={
                    'full_name': 'user.get_full_name',
                    'email': 'user.email',
                },
                field_labels={
                    'student_id': _('CLIPBOARD_STUDENT_IDS'),
                    'email': _('CLIPBOARD_EMAIL_ADDRESSES'),
                },
            )
        super().__init__(*args, **kwargs)


class JSONField(models.TextField):
    """
    Stores JSON object in a text field.
    """
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    @classmethod
    def parse_json(cls, value):
        if not value:
            return None
        if isinstance(value, str):
            try:
                return json.loads(value)
            except (TypeError, ValueError) as exc:
                raise exceptions.ValidationError(_('ERROR_ENTER_VALID_JSON')) from exc
        return value

    @classmethod
    def print_json(cls, value):
        if not value:
            return ""
        if isinstance(value, str):
            return value
        return json.dumps(value)

    def from_db_value(self, value, expression, connection): # pylint: disable=unused-argument
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
        field = super().formfield(**defaults)
        if not field.help_text:
            field.help_text = _('ERROR_ENTER_VALID_JSON')
        return field


class JSONFormField(forms.CharField):
    """
    A JSON text area.
    """
    def to_python(self, value):
        return JSONField.parse_json(value)

    def prepare_value(self, value):
        return JSONField.print_json(value)


# Overridden versions of Django's related descriptors.
# Used by `DefaultForeignKey` and `DefaultOneToOneField`.


class DefaultForwardManyToOneDescriptor(related_descriptors.ForwardManyToOneDescriptor):
    def get_queryset(self, **hints):
        return self.field.remote_field.model.objects.db_manager(hints=hints).all()


class DefaultForwardOneToOneDescriptor(related_descriptors.ForwardOneToOneDescriptor):
    def get_queryset(self, **hints):
        return self.field.remote_field.model.objects.db_manager(hints=hints).all()


class DefaultReverseOneToOneDescriptor(related_descriptors.ReverseOneToOneDescriptor):
    def get_queryset(self, **hints):
        return self.related.related_model.objects.db_manager(hints=hints).all()


class DefaultForeignKey(models.ForeignKey):
    """
    A `ForeignKey` that uses `objects` to access the related object.

    Django's `ForeignKey` uses the related model's base manager (which is
    usually `django.db.models.manager.Manager`) when accessing the related
    object. This means custom managers are not used. When using
    `DefaultForeignKey`, the related model's default manager (usually
    `objects`) is used when accessing the related object.
    """
    forward_related_accessor_class = DefaultForwardManyToOneDescriptor


class DefaultOneToOneField(models.OneToOneField):
    """
    A `OneToOneField` that uses `objects` to access the related object.

    Django's `OneToOneField` uses the related model's base manager (which is
    usually `django.db.models.manager.Manager`) when accessing the related
    object. This means custom managers are not used. When using
    `DefaultOneToOneField`, the related model's default manager (usually
    `objects`) is used when accessing the related object.
    """
    related_accessor_class = DefaultReverseOneToOneDescriptor
    forward_related_accessor_class = DefaultForwardOneToOneDescriptor
