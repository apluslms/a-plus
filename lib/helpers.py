import socket
import string
import functools
import warnings
from cachetools import cached, TTLCache
from collections import OrderedDict
from urllib.parse import parse_qs, parse_qsl, urlencode, urlsplit, urlunparse, urlunsplit, urlparse
from PIL import Image
from typing import Any, Dict, Iterable, List

from django.conf import settings
from django.utils.crypto import get_random_string as django_get_random_string
from django.utils.deprecation import RemovedInNextVersionWarning
from django.utils.translation import get_language


def deprecated(message):
    '''
    This is a decorator which can be used to mark functions
    as deprecated. It will result in a warning being emitted
    when the function is used.
    '''
    def wrapper(func):
        @functools.wraps(func)
        def new_func(*args, **kwargs):
            warnings.warn(message, category=RemovedInNextVersionWarning, stacklevel=2)
            return func(*args, **kwargs)
        return new_func
    return wrapper


def extract_form_errors(form):
    """
    Extracts Django form errors to a list of error messages.
    """
    errors = []
    for field in form.errors:
        for err in form.errors[field]:
            errors.append("%s: %s" % (field, err))
    return errors


def get_random_string(length=32, choices=None):
    """
    This function creates a random string with a given length.
    The strings consist of upper and lower case letters and numbers.

    @param length: the length of the randomized string, defaults to 32
    @return: a random string containing lower and upper case letters and digits
    """

    # Use all letters and numbers in the identifier
    if not choices:
        choices = string.ascii_letters + string.digits
    return django_get_random_string(length=length, allowed_chars=choices)


def query_dict_to_list_of_tuples(query_dict):
    """
    This helper function creates a list of tuples with the values
    from a QueryDict object. In a QueryDict the same key can have
    several values, which is not possible with a typical dict nor a JSON
    object. The resulting list will be similar to [(key1, value1), (key2, value2)].

    @param query_dict: a QueryDict object
    @return: a list of tuples with the same keys and values as in the given QueryDict
    """
    list_of_tuples = []
    for key in query_dict:
        for val in query_dict.getlist(key):
            list_of_tuples.append((key, val))
    return list_of_tuples


# Any is used here because Python's type hints can't ensure that the input
# iterable's 1st and 2nd item match the keys and values of the output dict,
# respectively.
def pairs_to_dict(pairs: Iterable[Iterable[Any]]) -> Dict[Any, List[Any]]:
    """
    Transforms the provided key-value-pairs into a dict. Each key may appear
    multiple times, which is why the output dict's values are lists. This can
    be used to turn the result of `query_dict_to_list_of_tuples` back into a
    dict (not a QueryDict).

    Example: `[["field_1", "1"], ["field_2", "a"], ["field_2", "b"]]` is
    transformed into `{"field_1": ["1"], "field_2": ["a", "b"]}`.
    """
    data: Dict[str, List[str]] = {}
    for key, value in pairs:
        if key in data:
            data[key].append(value)
        else:
            data[key] = [value]
    return data


def url_with_query_in_data(url: str, data: dict = {}): # pylint: disable=dangerous-default-value
    """
    Take an url with (or without) query parameters and a dictionary of data.
    Return url without query parameters and a dictionary with merged values from the query and the data.
    """
    scheme, netloc, path, query = urlsplit(url)[:4]
    query = dict(parse_qsl(query))
    query.update(data)
    return urlunsplit((scheme, netloc, path, None, None)), query


def update_url_params(url, params):
    delimiter = "&" if "?" in url else "?"
    return url + delimiter + urlencode(params)


def remove_query_param_from_url(url, param):
    """
    Take an url with (or without) query parameters. Return url without the selected query parameter.
    """
    url = urlsplit(url)
    query = parse_qs(url.query, keep_blank_values=True)
    query.pop(param, None)
    return urlunsplit(url._replace(query=urlencode(query, True)))


def build_aplus_url(url: str, user_url: bool = False) -> str:
    """
    Enforce that the given URL is a full absolute URL that always uses
    the network location from the configured BASE_URL. In some installations, particularly
    local docker environments, separate SERVICE_BASE_URL is used to distinguish the
    docker internal network addresses from user-facing address (typically localhost).
    Optional argument 'user_url' tells which one the caller is interested in.
    Takes URL as a parameter, returns (possibly) modified URL.
    """
    baseurl = settings.BASE_URL
    if not user_url and hasattr(settings, 'SERVICE_BASE_URL'):
        baseurl = settings.SERVICE_BASE_URL
    parsed = urlparse(url)
    baseparsed = urlparse(baseurl)
    parsed = parsed._replace(scheme=baseparsed.scheme, netloc=baseparsed.netloc)
    return urlunparse(parsed)


FILENAME_CHARS = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ._-0123456789"

def safe_file_name(name):
    safename = "".join(c for c in name if c in FILENAME_CHARS)
    if safename[0] == "-":
        return "_" + safename[1:80]
    return safename[:80]


def resize_image(path, max_size):
    image = Image.open(path)
    image.thumbnail(max_size, Image.LANCZOS)
    image.save(path)


def roman_numeral(number):
    numbers = [1000,900,500,400,100,90,50,40,10,9,5,4,1];
    letters = ["M","CM","D","CD","C","XC","L","XL","X","IX","V","IV","I"];
    roman = ""
    for i in range(len(numbers)): # pylint: disable=consider-using-enumerate
        while number >= numbers[i]:
            roman += letters[i]
            number -= numbers[i]
    return roman


def settings_text(key):
    def get(name):
        if hasattr(settings, name):
            return getattr(settings, name)
        return None
    return get('{}_{}'.format(key, (get_language() or settings.LANGUAGE_CODE).upper())) or get(key)


@cached(TTLCache(100, ttl=30))
def get_url_ip_address_list(url):
    """
    This function takes a full URL as a parameter and returns the IP addresses
    of the host as a string.

    It will cache results for 30 seconds, so repeated calls return fast
    """
    hostname = urlsplit(url).hostname
    assert hostname, "Invalid url: no hostname found"
    ips = (a[4][0] for a in socket.getaddrinfo(hostname, None, 0, socket.SOCK_STREAM, socket.IPPROTO_TCP))
    return tuple(set(ips))


def get_remote_addr(request):
    real_ip = request.META.get('HTTP_X_REAL_IP')
    if real_ip:
        return real_ip
    forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if forwarded_for:
        return forwarded_for.split(',', 1)[0].strip()
    return request.META.get('REMOTE_ADDR')


def show_debug_toolbar(request):
    """Return True if the Django Debug Toolbar should be shown on a given page."""
    return settings.ENABLE_DJANGO_DEBUG_TOOLBAR and request.META.get("REMOTE_ADDR") in settings.INTERNAL_IPS


def format_points(points: int, is_revealed: bool, is_container: bool) -> str:
    """
    Formats a number of points to be displayed in the UI. The formatting
    depends on two parameters:

    `is_revealed`: False if the points are for an exercise whose feedback is
    hidden, or if the points are for a module/category that contains at least
    one exercise whose feedback is hidden. Otherwise true.

    `is_container`: False if the points are for an exercise or a submission.
    Otherwise true.
    """
    if is_revealed:
        return str(points)
    if is_container:
        return f'{points}+'
    return '?'


class Enum:
    """
    Represents constant enumeration.

    Usage:
        OPTS = Enum(
            ('FOO', 1, 'help string for foo'),
            ('BAR', 2, 'help string for bar'),
        )

        if OPTS.FOO == test_var:
            return OPTS[test_var]

        ChoicesField(choices=OPTS.choices)
    """
    def __init__(self, *choices):
        if len(choices) == 1 and isinstance(choices[0], list):
            choices = choices[0]
        self._strings = OrderedDict()
        self._keys = []
        for name, value, string in choices: # noqa: F402
            assert value not in self._strings, "Multiple choices have same value"
            self._strings[value] = string
            self._keys.append(name)
            setattr(self, name, value)

    @property
    def choices(self):
        return tuple(sorted(self._strings.items()))

    def keys(self):
        return (x for x in self._keys)

    def values(self):
        return (x for x in self._strings)

    def __contains__(self, value):
        return value in self._strings

    def __getitem__(self, key):
        return self._strings[key]

    def __str__(self):
        s = ["<%s([" % (self.__class__.__name__,)]
        for key in self.keys():
            val = getattr(self, key)
            txt = self[val]
            s.append("  (%s, %s, %s)," % (key, val, txt))
        s.append("])>")
        return '\n'.join(s)
