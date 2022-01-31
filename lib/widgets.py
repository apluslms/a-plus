from typing import Any, Dict, List, Optional, Tuple

from django import forms
from django.template import Variable


class DateTimeLocalInput(forms.DateTimeInput):
    """
    A datetime widget that uses the `datetime-local` input type in HTML.

    The initial value of the HTML input must be formatted `YYYY-MM-DDThh:mm`.
    This widget ensures proper formatting.

    The submitted form also uses this format, which Django can already handle
    without custom logic (see `django.utils.dateparse.datetime_re`).
    """
    input_type = 'datetime-local'

    def __init__(self, attrs: Optional[Dict[str, Any]] = None) -> None:
        default_attrs = {'step': 1} # Display seconds in widget
        if attrs is not None:
            default_attrs.update(attrs)
        super().__init__(attrs=default_attrs, format='%Y-%m-%dT%H:%M')


class DurationInput(forms.MultiWidget):
    """
    A widget for entering a duration of time.

    Renders as a row of text boxes, one for each given unit of time (e.g. days,
    hours and minutes).

    Use with `lib.fields.DurationField`.
    """
    units: List[Tuple[str, int]]

    def __init__(self, units: List[Tuple[str, int]], attrs: Optional[Dict[str, Any]] = None) -> None:
        self.units = units
        widgets = [forms.NumberInput({'placeholder': name}) for name, factor in self.units]
        default_attrs = {'class': 'duration-input'}
        if attrs is not None:
            default_attrs.update(attrs)
        super().__init__(widgets, default_attrs)

    def decompress(self, value: Optional[int]) -> List[Optional[int]]:
        """
        Converts the given minute value into the different units.
        """
        if value is None:
            return [None] * len(self.units)
        remainder = value
        unit_values = []
        for name, factor in self.units:
            unit_values.append(remainder // factor)
            remainder = remainder % factor
        return unit_values

    def value_from_datadict(self, data: Dict[str, Any], files: Dict[str, List[Any]], name: str) -> Any:
        """
        Extract every individual unit's value from a submitted data dictionary.

        If instead of different units, a single value is submitted (i.e.
        request was probably not made using a HTML form), use that as the base
        unit and set every other unit to None.
        """
        if name in data:
            value = [None] * len(self.units)
            value[-1] = data[name]
            return value
        return super().value_from_datadict(data, files, name)


class SearchSelect(forms.SelectMultiple):
    """
    A multi-select widget with search, copy and paste functionality.

    Explanations of the initialization parameters:

    * `ajax`: whether the widget should query the API to get suggestions.
    * `display_fields`: names of fields that comprise the display name of an
      instance. If not provided, the field's `label_from_instance` method will
      be used to create the display name.
    * `clipboard_fields`: names of the fields whose values can be copied and
      pasted as a comma-separated list. If not provided, only the IDs of the
      selected instances can be copied and pasted.
    * `field_sources`: maps field names to their sources. Provide sources for
      the fields that do not exist in the instance. The source string uses the
      same syntax as Django templates.
    * `field_labels`: maps field names to their labels. The label appears in
      the copy/paste menus.
    * `search_api_url`: URL of the API endpoint that will be queried if `ajax`
      is `True`. The field names mentioned in the previous parameters should
      match the fields returned by this endpoint. The endpoint must support the
      "search", "field" and "values" GET query parameters since those are used
      in queries.
    """
    template_name = 'ajax_search_select.html'

    class Media:
        js = ('js/ajax_search_select.js',)

    def __init__(
            self,
            ajax: bool = False,
            display_fields: Optional[List[str]] = None,
            clipboard_fields: Optional[List[str]] = None,
            field_sources: Optional[Dict[str, str]] = None,
            field_labels: Optional[Dict[str, str]] = None,
            search_api_url: Optional[str] = None,
            *args: Any,
            **kwargs: Any,
            ) -> None:
        super().__init__(*args, **kwargs)
        self.ajax = ajax
        self.display_fields = display_fields or []
        self.clipboard_fields = clipboard_fields or []
        self.field_sources = field_sources or {}
        self.field_labels = field_labels or {}
        self.search_api_url = search_api_url

    def get_context(self, name: str, value: Any, attrs: Optional[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Get data used to render the widget.
        Overrides `Widget.get_context`.
        """
        context = super().get_context(name, value, attrs)
        # Keep the attributes of this widget and the inner widget and separate.
        context['inner_widget'] = context['widget']
        context['widget'] = {
            'attrs': {
                'id': context['inner_widget']['attrs']['id'] + '_wrapper',
                'class': 'search-select-ajax' if self.ajax else 'search-select',
                'data-display-fields': ','.join(self.display_fields),
                'data-clipboard-fields': ','.join(self.clipboard_fields),
                'data-search-api-url': self.search_api_url or '',
            }
        }
        context['clipboard_options'] = [
            {'field': field, 'label': self.field_labels.get(field, field)}
            for field in self.clipboard_fields
        ]
        return context

    def create_option(self, name: str, value: Any, *args: Any, **kwargs: Any) -> Dict[str, Any]:
        """
        Get the data used to render a single option in the widget.
        Overrides `ChoiceWidget.create_option`.
        """
        result = super().create_option(name, value, *args, **kwargs)

        # Replace the label with a custom one, if display fields are provided.
        if self.display_fields:
            result['label'] = ", ".join((
                self.get_field_value(value.instance, field)
                for field in self.display_fields
            ))

        # Add the data-* attributes that are used for copy/paste functionality.
        result['attrs'].update({
            f'data-{field}': self.get_field_value(value.instance, field)
            for field in self.clipboard_fields
        })

        return result

    def get_field_value(self, instance: Any, field: str) -> str:
        """
        Get the value of a field in an object as a string.
        """
        if field in self.field_sources:
            # Use the same syntax as Django templates for the field source.
            value = Variable(self.field_sources[field]).resolve(instance)
        else:
            value = getattr(instance, field, None)
        return str(value) if value is not None else ''
