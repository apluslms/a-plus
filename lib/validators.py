import functools
import re

from django.core.validators import RegexValidator
from django.utils.translation import ugettext_lazy as _

# The URL key (slug) for a course, course instance, course module, or learning object.
# The key must not consist of only the period (.) since it would be interpreted
# as a relative path in the URL.
generate_url_key_validator = functools.partial(RegexValidator,
    regex=re.compile(r"^\w[\w\-\.]*$"),
    message=_("URL keys may consist of alphanumeric characters, hyphen and period."))
