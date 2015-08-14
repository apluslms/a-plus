'''
The exercises and classes are configured in json.
Each directory inside exercises/ holding an index.json is a course.
'''
from django.conf import settings
from django.utils.module_loading import import_by_path
import os, time, json, yaml, re
import docutils.core
import logging
import copy

DIR = os.path.join(settings.BASE_DIR, "exercises")
INDEX = "index"
DEFAULT_LANG = "en"

LOGGER = logging.getLogger('main')

def iterate_kvp_with_dfs(node, key_regex=None):
    '''
    Iterate the key-value-parent tuples of a dictionary (or list) 'node'
    recursively with DFS.
    
    @type node: C{dict}
    @param node: the dictionary (or list) to iterate
    @type key_regex: C{re.RegexObject}
    @param key_regex: the key based item filter regex (optional)
    '''
    # Compile the regex (if uncompiled)
    if isinstance(key_regex, str):
        key_regex = re.compile(key_regex)
    # Define an iterator
    if isinstance(node, dict):
        iterator = node.items()
    elif isinstance(node, list):
        iterator = enumerate(node)
    else:
        raise TypeError
    # Start the iteration
    for child_key, child_value in iterator:
        # Iterate subtree recursively
        if isinstance(child_value, dict) or isinstance(child_value, list):
            for sub_key, sub_value, sub_node in iterate_kvp_with_dfs(child_value, key_regex):
                yield sub_key, sub_value, sub_node
        # Ignore non matching items
        if key_regex and not key_regex.match(unicode(child_key)):
            continue
        # Yield matching items
        yield child_key, child_value, node


def get_rst_as_html(rst_str):
    '''
    Return a string with RST formatting as HTML.

    @type rst_str: C{str}
    @param rst_str: the RST string to convert
    @rtype : C{str}
    @return: the resulting HTML string
    '''
    parts = docutils.core.publish_parts(source=rst_str, writer_name='html')
    return parts['fragment']


class ConfigError(Exception):
    '''
    Configuration errors.
    '''
    def __init__(self, value, error=None):
        self.value = value
        self.error = error

    def __str__(self):
        if self.error is not None:
            return "%s: %s" % (repr(self.value), repr(self.error))
        return repr(self.value)


class ConfigParser:
    '''
    Provides configuration data parsed and automatically updated on change.
    '''
    FORMATS = {
        'json': json.load,
        'yaml': yaml.load
    }
    PROCESSOR_TAG_REGEX = re.compile(r'^(.+)\|(\w+)$')
    PROCESSOR_TAG_REGEX_18N = re.compile(r'^.+\|18n(\|.+)?$')
    TAG_PROCESSOR_DICT = {
        '18n': lambda root, parent, value, **kwargs: value[kwargs['lang']],
        'rst': lambda root, parent, value, **kwargs: get_rst_as_html(value),
    }

    def __init__(self):
        '''
        The constructor.
        '''
        self._courses = {}
        self._dir_mtime = 0


    def courses(self):
        '''
        Gets all courses.
        
        @rtype: C{list}
        @return: listed course configurations
        '''
        # Only if the course root dir has changed since last scan
        t = os.path.getmtime(DIR)
        if self._dir_mtime < t:
            self._dir_mtime = t
            LOGGER.debug('Reloading course indices...')
            # Load each directory having the index file as a course.
            for item in os.listdir(DIR):
                try:
                    self._get_config(os.path.join(DIR, item, INDEX))
                except ConfigError:
                    # Ignore extra items and malconfigured course directories
                    # silently
                    continue
                self._course_root(item)

        # Pick course data into list.
        course_list = []
        for c in self._courses.itervalues():
            course_list.append(c["data"])
        return course_list


    def course_entry(self, course_key):
        '''
        Gets a course entry.
        
        @type course_key: C{str}
        @param course_key: a course key
        @rtype: C{dict}
        @return: course configuration or None
        '''
        root = self._course_root(course_key)
        return None if root is None else root["data"]


    def exercises(self, course_key):
        '''
        Gets course exercises for a course key.
        
        @type course_key: C{str}
        @param course_key: a course key
        @rtype: C{tuple}
        @return: course configuration or None, listed exercise configurations or None
        '''
        course_root = self._course_root(course_key)
        if course_root is None:
            return (None, None)

        LOGGER.debug('Reloading exercises for %s', course_key)
        exercise_list = []
        for exercise_key in course_root["data"]["exercises"]:
            _, exercise = self.exercise_entry(course_root, exercise_key)
            if exercise is None:
              raise ConfigError("Invalid exercise key listed in \"%s\"!" % (course_root["file"]))
            exercise_list.append(exercise)
        return (course_root["data"], exercise_list)


    def exercise_entry(self, course, exercise_key, lang=None):
        '''
        Returns the data dicts for matching the given course and exercise keys.
        
        The function also accepts a course root dict instead of the course key.

        @type course: C{str|dict}
        @param course: a course key or root dict
        @type exercise_key: C{str}
        @param exercise_key: an exercise key
        @rtype: C{tuple}
        @return: course configuration or None, exercise configuration or None
        '''
        # Handle the `course` argument
        if isinstance(course, dict):
          course_root, course_key = course, course['data']['key']
        else:
          course_root, course_key = self._course_root(course), course
        LOGGER.debug('Fetching exercise \"%s/%s\" with lang=\"%s\"', course_key, exercise_key, lang)
        if course_root is None:
            # No such course
            return None, None
        if exercise_key not in course_root["data"]["exercises"]:
            # Unindexed exercise
            return course_root["data"], None
        # Load the exercise and return its data dict if found
        exercise_root = self._exercise_root(course_root, exercise_key)
        if not exercise_root or "data" not in exercise_root or not exercise_root["data"]:
            # Removed, non-existant exercise or empty exercise
            return course_root["data"], None
        # Return the exercise for the given language or the one for the
        # course's primary language
        for lang in lang, course_root["lang"]:
            if lang in exercise_root["data"]:
                return course_root["data"], exercise_root["data"][lang]
        # In case there was no exercise version for neither the requested nor
        # the course\'s primary language, return any version available
        return course_root["data"], list(exercise_root["data"].values())[0]


    def _course_root(self, course_key):
        '''
        Gets course dictionary root holding also system data.
        
        @type course_key: C{str}
        @param course_key: a course key
        @rtype: C{dict}
        @return: course root or None
        '''
        try:
            # Find out the full path to the course index config file
            f = self._get_config(os.path.join(DIR, course_key, INDEX))
        except ConfigError:
            # Return if it has been removed (or never existed).
            return None

        # Return the cached data if the index file has not been modified since
        # last load.
        t = os.path.getmtime(f)
        if course_key in self._courses and self._courses[course_key]["mtime"] >= t:
            return self._courses[course_key]

        # (Re)load the index.
        data = self._parse(f)
        if data is None:
            raise ConfigError("Failed to parse configuration file \"%s\"!" % (f))
        self._check_fields(f, data, ["name", "contact", "exercises"])
        # Add the course key into the data dict
        data["key"] = course_key
        # Determine the course's exercise loader function
        exercise_loader = self._default_exercise_loader
        if "exercise_loader" in data:
            exercise_loader = import_by_path(data["exercise_loader"])
        # Determine the course's primary language
        lang = data["lang"] if "lang" in data else DEFAULT_LANG

        self._courses[course_key] = {
            "file": f,
            "mtime": t,
            "ptime": time.time(),
            "data": data,
            "lang": lang,
            "exercise_loader": exercise_loader,
            "exercises": {}
        }
        return self._courses[course_key]


    def _exercise_root(self, course_root, exercise_key):
        '''
        Gets exercise dictionary root holding also system data.
        
        @type course_root: C{dict}
        @param course_root: a course root dictionary
        @type exercise_key: C{str}
        @param exercise_key: an exercise key
        @rtype: C{dict}
        @return: exercise root or None
        '''
        # If the exercise exists in the course exercise cache
        if exercise_key in course_root["exercises"]:
            exercise_root = course_root["exercises"][exercise_key]
            # Return the cached root if the exercise's main config file has
            # not been touched after last (re)load
            f, ptime = exercise_root["file"], exercise_root["ptime"]
            if os.path.isfile(f) and os.path.getmtime(f) < ptime:
                return exercise_root

        LOGGER.debug('Reloading exercise "%s/%s"', course_root["data"]["key"], exercise_key)
        # Otherwise load the exercise using the course's exercise loader
        # (possibly the default `_default_exercise_loader`)
        f, data = course_root["exercise_loader"](course_root, exercise_key, \
                os.path.join(DIR, course_root["data"]["key"]))
        # Return `None` if nothing could be loaded or the returned file does
        # not exist
        if not os.path.isfile(f) or not data:
            return None
        # Add the exercise key into the data dict
        data["key"] = exercise_key # FIXME: The key is now in all language
        # versions and (see below) the data root!
        # Process any tagged items in the data dict and create the language
        # versions
        self._process_exercise_data(course_root, data)
        # Check that all it's language versions contain the required fields
        for version in data.values():
            self._check_fields(f, version, ["title", "view_type", "key"])
        # Add the exercise key into the data dict
        data["key"] = exercise_key # FIXME
        # Define the root
        course_root["exercises"][exercise_key] = exercise_root = {
            "file": f,
            "mtime": os.path.getmtime(f),
            "ptime": time.time(),
            "data": data
        }
        # Return it
        return exercise_root


    def _check_fields(self, file_name, data, field_names):
        '''
        Verifies that a given dict contains a set of keys.

        @type key: C{str}
        @param key: configuration file key
        @type entry: C{dict}
        @param entry: a configuration entry
        @type field_names: C{tuple}
        @param field_names: required field names
        '''
        for name in field_names:
            if name not in data:
                raise ConfigError("Required field \"%s\" missing from \"%s\"!" % (name, file_name))


    def _get_config(self, path):
        '''
        Returns the full path to the config file identified by a path or None.

        Raises error if there are multiple rivalling config files or no config
        at all.

        @type path: C{str}
        @param path: a path to a config file, possibly without a suffix
        @rtype: C{str}
        @return: the full path to the corresponding config file
        '''
        # Return it directly if the given path already is a full path and has
        # a supported extension
        if os.path.isfile(path):
            ext = os.path.splitext(path)[1]
            if len(ext) > 0 and ext[1:] in self.FORMATS:
                return path
        config_file = None
        # If the directory where the config should exist does exist
        if os.path.isdir(os.path.dirname(path)):
            # Scan for files with a supported file format extension
            for ext in self.FORMATS.keys():
                f = "%s.%s" % (path, ext)
                if os.path.isfile(f):
                    if config_file != None:
                        raise ConfigError("Multiple config files for \"%s\"!" % (path))
                    config_file = f
        # Raise an error if no config file could be found
        if not config_file:
            raise ConfigError("No supported config at \"%s\"!" % (path))
        return config_file


    def _parse(self, path, loader=None):
        '''
        Parses a dict from a file.

        If no `loader` function is given, the class's default loaders are
        used.

        @type path: C{str}
        @param path: a path to a file
        @type loader: C{function}
        @param loader: a configuration file stream parser
        @rtype: C{dict}
        @return: an object representing the configuration file or None
        '''
        if not loader:
            try:
                loader = self.FORMATS[os.path.splitext(path)[1][1:]]
            except:
                raise ConfigError("Unsupported format \"%s\"" % (path))
        data = None
        with open(path) as f:
            try:
                data = loader(f)
            except ValueError as e:
                raise ConfigError("Configuration error in %s" % (path), e)
        return data


    def _default_exercise_loader(self, course_root, exercise_key, course_dir):
        '''
        Return the exercise config file path and exercise data dict
        corresponding to the given arguments.

        Raises error if there are problems with finding or loading the correct
        config file.

        @type course_root: C{dict}
        @param course_root: a course root dictionary
        @type exercise_key: C{str}
        @param exercise_key: an exercise key
        @type course_dir: C{str}
        @param course_dir: a path to the course root directory
        @rtype: C{str}, C{dict}
        @return: exercise config file path and exercise data dict
        '''
        # Fetch the exercise's config file
        config_file = self._get_config(os.path.join(course_dir, exercise_key))
        # Parse and return the data.
        return config_file, self._parse(config_file)


    def _process_exercise_data(self, course_root, data):
        '''
        Process a data dictionary according to embedded processor flags.

        In essence, the function makes copies of itself for each unique
        language mentioned in fields that have the '18n' tag. and then
        for each language 'fork' or 'version' it processes the remaining tags.
        In case there's no usage of the '18n' tag the dict processed as being
        the language version for to the course's primary language.

        @type course_root: C{dict}
        @param course_root: a course root dictionary
        @type data: C{dict}
        @param data: a config data dictionary to process (in-place)
        '''
        # Scan the data dictionary for keys with the `18n` tag and initialize
        # a duplicate of the entire data dict for each unique (language) key
        # found as an immediate child of a tagged key (`title|18n: {fi: foo, en: bar}`)
        lang_root = {}
        for k, v, p in iterate_kvp_with_dfs(data, key_regex=self.PROCESSOR_TAG_REGEX_18N):
            for lang in v.keys():
                if lang not in lang_root:
                    lang_root[lang] = copy.deepcopy(data)
        LOGGER.debug('i18n-language versions: %d (%s)', len(lang_root), list(lang_root.keys()))
        # Read the course's primary language
        lang = course_root['lang']
        # If the exercise data dict has no language versioning, the data is by
        # default associated with the course's primary language
        if len(lang_root) == 0:
            lang_root = {lang: copy.deepcopy(data)}
        # Clear the original data dict
        data.clear()
        # Assing the children of `lang_root` to the original data dict
        data.update(lang_root)
        # Note: At this point the data dict contains itself duplicated for
        # each unique language key encountered (or at least the course's
        # primary language).
        # Initialize tags processed count counter
        tags_processed_count = 0
        # Process each fork (copy of the data dict) with it's language
        for lang, fork in data.items():
            for k, v, p in iterate_kvp_with_dfs(fork, key_regex=self.PROCESSOR_TAG_REGEX):
                # Loop processing the right-most key tag until all tags are
                # processed
                while True:
                    match = self.PROCESSOR_TAG_REGEX.match(k)
                    if not match:
                        break
                    # Remove old key-value from the dict
                    del p[k]
                    # Extract the new key (with the tag stripped) and the tag
                    k, tag = match.groups()
                    # Raise error if the tag is unrecognized
                    if tag not in self.TAG_PROCESSOR_DICT:
                        raise ConfigError('Unsupported processor tag "%s"!' % (tag))
                    # Process the value with the corresponding processor and
                    # save it under the new key
                    p[k] = v = self.TAG_PROCESSOR_DICT[tag](fork, p, v, lang=lang)
                    tags_processed_count += 1
        LOGGER.debug('Number of processed tags: %d', tags_processed_count)
