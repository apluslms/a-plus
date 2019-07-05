import os
import re
from urllib.parse import unquote


def colons(string):
    if string[0] != ':':
        string = ':' + string
    if string[-1] != ':':
        string += ':'
    return string


def shib_join(*strings):
    strings = (x.replace(r';', r'\;') for x in strings)
    return ';'.join(strings)


RAISE_KEYERROR = 'KeyError()'


class Parser:
    DELIM = re.compile(r'(?<!\\);')

    def __init__(self, *, urldecode=False, filter_map=None, env=None):
        self._urldecode = urldecode
        if not filter_map:
            filter_map = {}
        self._filter_map = {colons(k): v for k, v in filter_map.items()}
        self._env = env if env is not None else os.environ

    def get_values(self, name, default=RAISE_KEYERROR):
        try:
            values = self._env[name.upper()]
        except KeyError:
            if default is RAISE_KEYERROR:
                raise
            return [default]
        if self._urldecode:
            values = unquote(values)
        values = self.DELIM.split(values)
        values = [x.replace(r'\;', r';') for x in values]
        return values

    def get_single_value(self, name, default=RAISE_KEYERROR):
        values = self.get_values(name, default=default)
        if len(values) != 1:
            raise ValueError(
                "Environment variable has %d values, but only one is accepted. "
                "%s=%s" % (len(values), name, values))
        return values[0]

    def get_urn_values(self, urn, name, *, filters=None):
        urn = colons(urn)
        if filters is None:
            filters = self._filter_map.get(urn)
        fields = self.get_values(name)
        data = []
        for field in fields:
            if not field:
                continue
            if not field.startswith('urn:'):
                raise ValueError(
                    "Environment variable %s values have to start with 'urn:'. "
                    "Content is %s" % (name, fields))
            ns, _, value = field[3:].partition(urn)
            values = tuple(reversed(value.split(':'))) + (ns.lstrip(':'), field)
            if filters and not all(values[i] == v for i, v in filters.items()):
                continue
            data.append(values)
        return data
