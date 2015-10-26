from random import choice
from PIL import Image
import string
import urllib


def extract_form_errors(form):
    """
    Extracts Django form errors to a list of error messages.
    """
    errors = []
    for field in form.errors:
        for err in form.errors[field]:
            errors.append("%s: %s" % (field, err))
    return errors


def get_random_string(length=32):
    """
    This function creates a random string with a given length.
    The strings consist of upper and lower case letters and numbers.

    @param length: the length of the randomized string, defaults to 32
    @return: a random string containing lower and upper case letters and digits
    """

    # Use all letters and numbers in the identifier
    choices = string.ascii_letters + string.digits

    return ''.join([choice(choices) for _ in range(length)])


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


def update_url_params(url, params):
    delimiter = "&" if "?" in url else "?"
    return url + delimiter + urllib.parse.urlencode(params)


FILENAME_CHARS = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ._-"

def safe_file_name(name):
    safename = "".join(c for c in name if c in FILENAME_CHARS)
    if safename[0] == "-":
        return "_" + safename[1:80]
    return safename[:80]


def resize_image(path, max_size):
    image = Image.open(path)
    image.thumbnail(max_size, Image.ANTIALIAS)
    image.save(path)
