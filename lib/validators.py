import functools
import re

from django.core.validators import RegexValidator
from django.utils.translation import gettext_lazy as _

# The URL key (slug) for a course, course instance, course module, or learning object.
# The key must not consist of only the period (.) since it would be interpreted
# as a relative path in the URL.
generate_url_key_validator = functools.partial(RegexValidator,
    regex=re.compile(r"^\w[\w\-\.]*$"),
    message=_('URL_KEY_MAY_CONSIST_OF'))
