# Python
import string
from random import choice
import urllib.request, urllib.parse, urllib.error
import urllib.parse

def get_random_string(length=32):
    """ This function creates a random string with a given length. 
        The strings consist of upper and lower case letters and numbers. 
        @param length: the length of the randomized string, defaults to 32
        @return: a random string containing lower and upper case letters and digits
        """
    
    # Use all letters and numbers in the identifier
    choices = string.ascii_letters + string.digits
    
    # Return a joined string of 'length' random characters
    return ''.join([choice(choices) for i in range(length)])

def query_dict_to_list_of_tuples(query_dict):
    """ This helper function creates a list of tuples with the values
        from a QueryDict object. In a QueryDict the same key can have 
        several values, which is not possible with a typical dict nor a JSON
        object. The resulting list will be similar to [(key1, value1), (key2, value2)].
        
        @param query_dict: a QueryDict object
        @return: a list of tuples with the same keys and values as in the given QueryDict
        """
    list_of_tuples = []
    for key in query_dict:
        for val in query_dict.getlist(key):
            list_of_tuples.append( (key, val) )
    return list_of_tuples

def update_url_params(url, params):
    url_parts = list(urllib.parse.urlparse(url))
    query = dict(urllib.parse.parse_qs(url_parts[4]))
    query.update(params)

    url_parts[4] = urllib.parse.urlencode(query)

    return urllib.parse.urlunparse(url_parts)
