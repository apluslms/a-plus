from typing import Any, Dict, Optional

from django import forms


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
