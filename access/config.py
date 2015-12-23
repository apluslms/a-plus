'''
The exercises and classes are configured in json/yaml.
Each directory inside exercises/ holding an index.json/yaml is a course.
'''
from django.conf import settings
from django.utils.module_loading import import_by_path
import os, time, json, yaml, re
import logging
import copy

from util.dict import iterate_kvp_with_dfs, get_rst_as_html


DIR = os.path.join(settings.BASE_DIR, "exercises")
INDEX = "index"
DEFAULT_LANG = "en"

LOGGER = logging.getLogger('main')


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
    PROCESSOR_TAG_REGEX_18N = re.compile(r'^.+\|i18n(\|.+)?$')
    PROCESSOR_TAG_REGEX = re.compile(r'^(.+)\|(\w+)$')
    TAG_PROCESSOR_DICT = {
        'i18n': lambda root, parent, value, **kwargs: value[kwargs['lang']],
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
        @return: course configurations
        '''

        # Find all courses if exercises directory is modified.
        t = os.path.getmtime(DIR)
        if self._dir_mtime < t:
            self._courses.clear()
            self._dir_mtime = t
            LOGGER.debug('Recreating course list.')
            for item in os.listdir(DIR):
                try:
                    self._course_root(item)
                except ConfigError:
                    LOGGER.exception("Failed to load course: %s", item)
                    continue

        # Pick course data into list.
        course_list = []
        for c in self._courses.values():
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

        # Pick exercise data into list.
        exercise_list = []
        for exercise_key in course_root["data"]["exercises"]:
            _, exercise = self.exercise_entry(course_root, exercise_key)
            if exercise is None:
                raise ConfigError('Invalid exercise key "%s" listed in "%s"'
                    % (exercise_key, course_root["file"]))
            exercise_list.append(exercise)
        return (course_root["data"], exercise_list)


    def exercise_entry(self, course, exercise_key, lang=None):
        '''
        Gets course and exercise entries for their keys.

        @type course: C{str|dict}
        @param course: a course key or root dict
        @type exercise_key: C{str}
        @param exercise_key: an exercise key
        @rtype: C{tuple}
        @return: course configuration or None, exercise configuration or None
        '''
        if isinstance(course, dict):
          course_root, course_key = course, course['data']['key']
        else:
          course_root, course_key = self._course_root(course), course

        if course_root is None:
            return None, None
        if exercise_key not in course_root["data"]["exercises"]:
            return course_root["data"], None

        exercise_root = self._exercise_root(course_root, exercise_key)
        if not exercise_root or "data" not in exercise_root or not exercise_root["data"]:
            return course_root["data"], None

        # Try to find version for requested or configured language.
        for lang in lang, course_root["lang"]:
            if lang in exercise_root["data"]:
                return course_root["data"], exercise_root["data"][lang]

        # Fallback to any existing language version.
        return course_root["data"], list(exercise_root["data"].values())[0]


    def _course_root(self, course_key):
        '''
        Gets course dictionary root (meta and data).

        @type course_key: C{str}
        @param course_key: a course key
        @rtype: C{dict}
        @return: course root or None
        '''

        # Try cached version.
        if course_key in self._courses:
            course_root = self._courses[course_key]
            try:
                if course_root["mtime"] >= os.path.getmtime(course_root["file"]):
                    return course_root
            except OSError:
                pass

        LOGGER.debug('Loading course "%s"' % (course_key))
        try:
            f = self._get_config(os.path.join(DIR, course_key, INDEX))
        except ConfigError:
            return None

        t = os.path.getmtime(f)
        data = self._parse(f)
        if data is None:
            raise ConfigError('Failed to parse configuration file "%s"' % (f))

        self._check_fields(f, data, ["name"])
        data["key"] = course_key

        if "modules" in data:
            keys = []
            config = {}
            def recurse_exercises(parent):
                if "children" in parent:
                    for exercise_vars in parent["children"]:
                        if "key" in exercise_vars and "config" in exercise_vars:
                            keys.append(exercise_vars["key"])
                            config[exercise_vars["key"]] = exercise_vars["config"]
                        recurse_exercises(exercise_vars)
            for module in data["modules"]:
                recurse_exercises(module)
            data["exercises"] = keys
            data["config_files"] = config

        # Enable course configurable ecercise_loader function.
        exercise_loader = self._default_exercise_loader
        if "exercise_loader" in data:
            exercise_loader = import_by_path(data["exercise_loader"])

        self._courses[course_key] = course_root = {
            "file": f,
            "mtime": t,
            "ptime": time.time(),
            "data": data,
            "lang": data["lang"] if "lang" in data else DEFAULT_LANG,
            "exercise_loader": exercise_loader,
            "exercises": {}
        }
        return course_root


    def _exercise_root(self, course_root, exercise_key):
        '''
        Gets exercise dictionary root (meta and data).

        @type course_root: C{dict}
        @param course_root: a course root dictionary
        @type exercise_key: C{str}
        @param exercise_key: an exercise key
        @rtype: C{dict}
        @return: exercise root or None
        '''

        # Try cached version.
        if exercise_key in course_root["exercises"]:
            exercise_root = course_root["exercises"][exercise_key]
            try:
                if exercise_root["mtime"] >= os.path.getmtime(exercise_root["file"]):
                    return exercise_root
            except OSError:
                pass

        LOGGER.debug('Loading exercise "%s/%s"', course_root["data"]["key"], exercise_key)
        file_name = exercise_key
        if "config_files" in course_root["data"]:
            file_name = course_root["data"]["config_files"].get(exercise_key, exercise_key)
        f, t, data = course_root["exercise_loader"](
            course_root,
            file_name,
            os.path.join(DIR, course_root["data"]["key"])
        )
        if not data:
            return None

        # Process key modifiers and create language versions of the data.
        self._process_exercise_data(course_root, data)
        for version in data.values():
            self._check_fields(f, version, ["title", "view_type"])
            version["key"] = exercise_key

        course_root["exercises"][exercise_key] = exercise_root = {
            "file": f,
            "mtime": t,
            "ptime": time.time(),
            "data": data
        }
        return exercise_root


    def _check_fields(self, file_name, data, field_names):
        '''
        Verifies that a given dict contains a set of keys.

        @type file_name: C{str}
        @param file_name: a file name for targeted error message
        @type data: C{dict}
        @param data: a configuration entry
        @type field_names: C{tuple}
        @param field_names: required field names
        '''
        for name in field_names:
            if name not in data:
                raise ConfigError('Required field "%s" missing from "%s"' % (name, file_name))


    def _get_config(self, path):
        '''
        Returns the full path to the config file identified by a path.

        @type path: C{str}
        @param path: a path to a config file, possibly without a suffix
        @rtype: C{str}
        @return: the full path to the corresponding config file
        @raises ConfigError: if multiple rivalling configs or none exist
        '''

        # Check for complete path.
        if os.path.isfile(path):
            ext = os.path.splitext(path)[1]
            if len(ext) > 0 and ext[1:] in self.FORMATS:
                return path

        # Try supported format extensions.
        config_file = None
        if os.path.isdir(os.path.dirname(path)):
            for ext in self.FORMATS.keys():
                f = "%s.%s" % (path, ext)
                if os.path.isfile(f):
                    if config_file != None:
                        raise ConfigError('Multiple config files for "%s"' % (path))
                    config_file = f
        if not config_file:
            raise ConfigError('No supported config at "%s"' % (path))
        return config_file


    def _parse(self, path, loader=None):
        '''
        Parses a dict from a file.

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
                raise ConfigError('Unsupported format "%s"' % (path))
        data = None
        with open(path) as f:
            try:
                data = loader(f)
            except ValueError as e:
                raise ConfigError("Configuration error in %s" % (path), e)
        return data


    def _default_exercise_loader(self, course_root, exercise_key, course_dir):
        '''
        Default loader to find and parse file.

        @type course_root: C{dict}
        @param course_root: a course root dictionary
        @type exercise_key: C{str}
        @param exercise_key: an exercise key
        @type course_dir: C{str}
        @param course_dir: a path to the course root directory
        @rtype: C{str}, C{dict}
        @return: exercise config file path, modified time and data dict
        '''
        config_file = self._get_config(os.path.join(course_dir, exercise_key))
        return config_file, os.path.getmtime(config_file), self._parse(config_file)


    def _process_exercise_data(self, course_root, data):
        '''
        Processes a data dictionary according to embedded processor flags
        and creates a data dict version for each language intercepted.

        @type course_root: C{dict}
        @param course_root: a course root dictionary
        @type data: C{dict}
        @param data: a config data dictionary to process (in-place)
        '''

        # Create a deep copy of data for each intercepted language.
        lang_root = {}
        for k, v, p in iterate_kvp_with_dfs(data, key_regex=self.PROCESSOR_TAG_REGEX_18N):
            for lang in v.keys():
                if lang not in lang_root:
                    lang_root[lang] = copy.deepcopy(data)
        default_lang = course_root["lang"]
        if not default_lang in lang_root:
            lang_root[default_lang] = copy.deepcopy(data)

        LOGGER.debug('Found %d language versions: %s', len(lang_root), list(lang_root.keys()))

        # Replace data with the language versions.
        data.clear()
        data.update(lang_root)

        # Apply processor flag transformations for data.
        tags_processed_count = 0
        for lang, lang_data in data.items():
            for k, v, p in iterate_kvp_with_dfs(lang_data, key_regex=self.PROCESSOR_TAG_REGEX):

                # Multiple processor flags may be combined.
                match = self.PROCESSOR_TAG_REGEX.match(k)
                while match:
                    del p[k]
                    k, tag = match.groups()
                    if tag not in self.TAG_PROCESSOR_DICT:
                        raise ConfigError('Unsupported processor tag "%s"' % (tag))
                    p[k] = v = self.TAG_PROCESSOR_DICT[tag](lang_data, p, v, lang=lang)

                    tags_processed_count += 1
                    match = self.PROCESSOR_TAG_REGEX.match(k)

        LOGGER.debug('Processed %d tags.', tags_processed_count)
