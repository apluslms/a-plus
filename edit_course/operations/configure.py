import copy
from dataclasses import dataclass
from datetime import datetime, timedelta
from functools import partial
import json
from typing import Any, Callable, Dict, List, Optional, Set, Tuple, Type

from aplus_auth.payload import Permission, Permissions
from aplus_auth.requests import get as aplus_get
from django.db import transaction
from django.utils import timezone
from django.utils.text import format_lazy
from django.utils.translation import gettext_lazy as _

from course.models import CourseInstance, CourseModule, LearningObjectCategory
from exercise.models import (
    LearningObject,
    CourseChapter,
    BaseExercise,
    LTIExercise,
    LTI1p3Exercise,
    RevealRule,
)
from external_services.models import LTIService, LTI1p3Service
from lib.localization_syntax import format_localization
from userprofile.models import UserProfile


def parse_date(value, errors, allow_null=False):
    if allow_null and value is None:
        return None
    for fmt in ['%Y-%m-%dT%H:%M:%SZ','%Y-%m-%dT%H:%M:%S','%Y-%m-%d %H:%M:%S',
        '%Y-%m-%d %H:%M','%Y-%m-%d %H','%Y-%m-%d']:
        try:
            return timezone.make_aware(datetime.strptime(str(value), fmt),
                timezone.get_current_timezone())
        except ValueError:
            pass
    errors.append(format_lazy(_('ERROR_PARSING_DATE -- {value}'), value=value))
    return None


def parse_duration(begin, value, errors):
    if len(value) > 1:
        try:
            i = int(value[:-1])
            if value[-1] == 'y':
                return timezone.make_aware(datetime(begin.year + i, begin.month,
                    begin.day, begin.hour, begin.minute, begin.second),
                    timezone.get_current_timezone())
            if value[-1] == 'm':
                yi = 0
                while begin.month + i > 12:
                    yi += 1
                    i = begin.month + i - 12
                return timezone.make_aware(datetime(begin.year + yi, begin.month + i,
                    begin.day, begin.hour, begin.minute, begin.second),
                    timezone.get_current_timezone())
            if value[-1] == 'd':
                return begin + timedelta(days=i)
            if value[-1] == 'h':
                return begin + timedelta(hours=i)
            if value[-1] == 'w':
                return begin + timedelta(weeks=i)
        except ValueError:
            pass
    errors.append(format_lazy(_('ERROR_PARSING_TIME_DURATION -- {value}'), value=value))
    return None


def parse_int(value, errors):
    try:
        return int(value)
    except ValueError:
        errors.append(format_lazy(_('ERROR_PARSING_INT -- {value}'), value=value))
    return None


def parse_float(value, errors):
    try:
        return float(value)
    except ValueError:
        errors.append(format_lazy(_('ERROR_PARSING_FLOAT -- {value}'), value=value))
    return None


def parse_bool(value):
    return value in [True, "true", "yes", "True", "Yes"]


def parse_choices(value, choices, field_name, errors):
    # value is the value in the JSON.
    # choices is a dict of accepted values:
    # it maps expected JSON values to the corresponding model/database field values.
    # field_name is the name of the JSON field.
    parsed_value = choices.get(value, None)
    if parsed_value is None:
        errors.append(
            format_lazy(
                _('ERROR_JSON_FIELD_UNKNOWN_VALUE -- {field}, {value}'),
                field=field_name,
                value=str(value),
            )
        )
        return None
    return parsed_value


def remove_newlines(value):
    # Replace all newlines with a space.
    # \r\n is done first to avoid two consecutive spaces.
    return value.replace('\r\n', ' ').replace('\n', ' ').replace('\r', ' ')


ChangesGetter = Callable[[dict, dict], Optional[dict]]


def get_config_changes(
        old: Dict[str, Any],
        new: Dict[str, Any],
        *,
        recurser: Optional[ChangesGetter] = None,
        keep: Optional[List[str]] = None,
        keep_unchanged: bool = False,
        ) -> Optional[Dict]:
    """Gets changes between configs.

    :param old: old config
    :param new: new config

    Keyword-only parameters:
    :param keep: fields in <new> to add to output as-is (unless no changes were detected,
    see the <keep_unchanged> param).
    :param keep_unchanged: whether to add fields in <keep> to output even when they
    have no changes. Fields in <keep> are normally not added to output
    if there were no changes in the dict itself. E.g. comparison of {"field": "value"} to
    itself will return None no matter what is in <keep> if <keep_unchanged> is False. If
    instead <keep> = "field" and <keep_unchanged> = True, the function returns
    {"field": "value"}.

    Returns None if <new> == <old> (and <keep_unchanged> is False). Otherwise:
    Finds the differences in dicts <new> and <old> where <recurser> is used to find differences
    between dict values. If the values for a key differ, the value in <new> is added to output.
    If the values are the same, the key is removed from the output.
    """
    if keep is None:
        keep = []

    if not keep_unchanged and old == new:
        return None

    # Keys to keep in output whether changed or not. This includes the ones
    # in <keep>, and the keys that are in <new> but not in <old>
    kept = new.keys() - (old.keys() - keep)
    # Keys that need to be compared: those that are in both dicts,
    # and are not in <keep>
    commonkeys_not_in_keep = old.keys() & new.keys() - keep

    diff = {key: new[key] for key in kept}
    for key in commonkeys_not_in_keep:
        if recurser is not None and isinstance(old[key], dict) and isinstance(new[key], dict):
            new_val = recurser(old[key], new[key])
            # Do not include the attribute if there were no changes
            if new_val is not None:
                diff[key] = new_val
        elif old[key] != new[key]:
            diff[key] = new[key]

    return diff


# Gets changes between two {lobj key: lobj config} -dicts
get_lobject_changes: ChangesGetter = partial(
    get_config_changes,
    recurser=partial(
        # We don't want to recurse any further to leave each field in the lobj intact.
        get_config_changes,
        keep=["children", "category", "target_category", "target_url", "max_submissions", "lti"]
    )
)


def lobject_class(config: dict) -> Type[LearningObject]:
    if "lti1p3" in config:
        return LTI1p3Exercise
    if "lti" in config:
        return LTIExercise

    if "max_submissions" in config:
        return BaseExercise

    return CourseChapter


def update_learning_objects( # noqa: MC0001
        category_map: Dict[str, LearningObjectCategory],
        configs: Dict[str, Dict[str, Any]],
        learning_objects: Dict[str, LearningObject],
        errors: List[str],
        ) -> None:
    """Configures learning objects.

    :param category_map: maps category keys to LearningObjectCategory objects
    :param configs: maps lobject keys to their configs
    :param learning_objects: maps lobject keys to LearningObject objects
    :param errors: list to append errors to
    """
    for key, o in configs.items():
        lobject = learning_objects[key]

        # Select exercise class.
        lobject_cls = lobject_class(o)

        if lobject_cls == LTIExercise:
            # validate_lobjects checks that this exists
            lobject.lti_service = LTIService.objects.filter(menu_label=str(o["lti"])).first()

            for key in [
                "context_id",
                "resource_link_id",
            ]:
                obj_key = "lti_" + key
                if obj_key in o:
                    setattr(lobject, key, o[obj_key])
            for key in (
                "aplus_get_and_post",
                "open_in_iframe",
            ):
                obj_key = "lti_" + key
                if obj_key in o:
                    setattr(lobject, key, parse_bool(o[obj_key]))

        if lobject_cls == LTI1p3Exercise:
            lobject.lti_service = LTI1p3Service.objects.filter(menu_label=str(o["lti1p3"])).first()
            if "lti_custom" in o:
                lobject.custom = o['lti_custom']
            if "lti_open_in_iframe" in o:
                lobject.open_in_iframe = o['lti_open_in_iframe']

        if lobject_cls in (LTIExercise, LTI1p3Exercise, BaseExercise):
            for key in [
                "allow_assistant_viewing",
                "allow_assistant_grading",
            ]:
                if key in o:
                    setattr(lobject, key, parse_bool(o[key]))
            for key in [
                "min_group_size",
                "max_group_size",
                "max_submissions",
                "max_points",
                "points_to_pass",
            ]:
                if key in o:
                    i = parse_int(o[key], errors)
                    if i is not None:
                        setattr(lobject, key, i)
            if "difficulty" in o:
                lobject.difficulty = o["difficulty"]
            for config_key, lobject_key in [
                ("reveal_submission_feedback", "submission_feedback_reveal_rule"),
                ("reveal_model_solutions", "model_solutions_reveal_rule"),
            ]:
                rule_config = o.get(config_key)
                if not rule_config:
                    continue
                if not isinstance(rule_config, dict) or "trigger" not in rule_config:
                    errors.append(format_lazy(_('REVEAL_RULE_ERROR_INVALID_JSON -- {key}'), key=config_key))
                    continue
                trigger = parse_choices(rule_config["trigger"], {
                    "immediate": RevealRule.TRIGGER.IMMEDIATE,
                    "manual": RevealRule.TRIGGER.MANUAL,
                    "time": RevealRule.TRIGGER.TIME,
                    "deadline": RevealRule.TRIGGER.DEADLINE,
                    "deadline_all": RevealRule.TRIGGER.DEADLINE_ALL,
                    "deadline_or_full_points": RevealRule.TRIGGER.DEADLINE_OR_FULL_POINTS,
                    "completion": RevealRule.TRIGGER.COMPLETION,
                }, "trigger", errors)
                rule = getattr(lobject, lobject_key)
                if not rule:
                    rule = RevealRule()
                rule.trigger = trigger
                if "time" in rule_config:
                    rule.time = parse_date(rule_config["time"], errors)
                if "delay_minutes" in rule_config:
                    rule.delay_minutes = parse_int(rule_config["delay_minutes"], errors)
                rule.save()
                setattr(lobject, lobject_key, rule)
            if "grading_mode" in o:
                grading_mode = parse_choices(o["grading_mode"], {
                    "best": BaseExercise.GRADING_MODE.BEST,
                    "last": BaseExercise.GRADING_MODE.LAST,
                }, "grading_mode", errors)
                lobject.grading_mode = grading_mode
            else:
                # If not explicitly specified, grading mode is determined by
                # the submission feedback reveal rule.
                rule = lobject.submission_feedback_reveal_rule
                if rule and rule.trigger != RevealRule.TRIGGER.IMMEDIATE:
                    lobject.grading_mode = BaseExercise.GRADING_MODE.LAST
                else:
                    lobject.grading_mode = BaseExercise.GRADING_MODE.BEST

        if lobject_cls == CourseChapter:
            if "generate_table_of_contents" in o:
                lobject.generate_table_of_contents = parse_bool(
                    o["generate_table_of_contents"])

        lobject.category = category_map[o["category"]]

        if "order" in o:
            lobject.order = parse_int(o["order"], errors)

        if "url" in o:
            lobject.service_url = format_localization(o["url"])
        if "status" in o:
            lobject.status = str(o["status"])
        if "audience" in o:
            words = { 'internal':1, 'external':2, 'registered':3 }
            lobject.audience = words.get(o['audience'], 0)
        if "title" in o:
            lobject.name = remove_newlines(format_localization(o["title"]))
        elif "name" in o:
            lobject.name = remove_newlines(format_localization(o["name"]))
        if not lobject.name:
            lobject.name = "-"
        if "description" in o:
            lobject.description = str(o["description"])
        if "use_wide_column" in o:
            lobject.use_wide_column = parse_bool(o["use_wide_column"])
        if "exercise_info" in o:
            lobject.exercise_info = o["exercise_info"]
        if "model_answer" in o:
            lobject.model_answers = format_localization(o["model_answer"])
        if "exercise_template" in o:
            lobject.templates = format_localization(o["exercise_template"])

        lobject.full_clean()
        lobject.save()


def get_build_log(instance):
    """
    Request latest build log from the build log URL defined for instance.
    """
    if not instance.build_log_url:
        return {'error': _('BUILD_LOG_ERROR_URL_BLANK')}
    try:
        permissions = Permissions()
        permissions.instances.add(Permission.READ, id=instance.id)
        response = aplus_get(instance.build_log_url, permissions=permissions)
    except Exception as e:
        return {
            'error': format_lazy(
                _('BUILD_LOG_ERROR_REQUESTING_FAILED -- {error!s}'),
                error=e,
            )
        }
    try:
        data = json.loads(response.text)
    except Exception as e:
        return {
            'error': format_lazy(
                _('BUILD_LOG_ERROR_PARSING_JSON -- {error!s}'),
                error=e,
            )
        }
    if not data:
        return {'error': _('BUILD_LOG_ERROR_EMPTY_LOG')}
    return data


def set_order_information(items: List[dict], n = 0) -> int:
    for o in items:
        if "order" not in o:
            n += 1
            o["order"] = n
    return n


def validate_lobject(
        config: dict,
        category_key_to_name: Dict[str,str],
        errors: List[str],
        ):
    """Check that config is valid.

    Only checks attributes that prevent saving.
    """
    if "key" not in config:
        errors.append(_('LEARNING_OBJECT_ERROR_REQUIRES_KEY'))
        return False
    if "category" not in config:
        errors.append(_('LEARNING_OBJECT_ERROR_REQUIRES_CATEGORY'))
        return False

    if config["category"] not in category_key_to_name:
        errors.append(
            format_lazy(
                _('LEARNING_OBJECT_ERROR_UNKNOWN_CATEGORY -- {category}'),
                category=config["category"],
            )
        )
        return False

    lobject_cls = lobject_class(config)

    if lobject_cls in (LTIExercise, LTI1p3Exercise):
        if lobject_cls == LTIExercise:
            conf = config["lti"]
            lti = LTIService.objects.filter(menu_label=str(conf)).first()
        else:
            conf = config["lti1p3"]
            lti = LTI1p3Service.objects.filter(menu_label=str(conf)).first()
        if not lti:
            errors.append(
                format_lazy(
                    _('LTI_ERROR_NO_CONFIGURATION_TO_SERVICE_USED_BY_EXERCISE -- {lti_label}, {exercise_key}'),
                    lti_label=str(conf),
                    exercise_key=config["key"],
                )
            )
            # The learning object can not be saved without an LTI service
            # since the foreign key is required.
            return False

    return True


@dataclass
class ConfigParts:
    """
    Contains the course config split into separate fields for easier handling.

    The version returned by ConfigParts.diff has a few specialties:
    - categories, modules, and module_lobjects only contain the changed fields
    and some supplemental fields that are required elsewhere. E.g. to identify
    the lobject class type.
    - *_names and *_keys fields contain whatever the <new> config contained. I.e. they
    contain the set of all such keys. E.g. module_keys contains the keys of
    all modules in the <new> config. They can be used to determined whether
    a module, exercise, etc. still exists in the course config even if nothing
    has changed (e.g. module config disappears from the modules field in the
    .diff() result if it had no changes).
    """
    config: Dict[Any, Any]

    # category name -> (category key, category config)
    categories: Dict[str, Tuple[Any, Dict[Any, Any]]]
    category_names: Set[str]
    # category name -> category key
    category_key_map: Dict[str, str]

    modules: Dict[str, Dict[Any, Any]]
    module_keys: Set[str]

    module_lobjects: Dict[str, Dict[str, Any]]
    module_lobject_keys: Dict[str, Set[Any]]

    @staticmethod
    def from_config(config: dict, errors: List[str]):
        categories_config = {}
        category_key_to_name = {}
        for category_key, c in config.get("categories", {}).items():
            if "name" not in c:
                errors.append(_('COURSE_CONFIG_ERROR_CATEGORY_REQUIRES_NAME'))
                continue

            name = format_localization(c["name"])
            categories_config[name] = (category_key,c)
            category_key_to_name[category_key] = name

        # Set module order information
        set_order_information(config.get("modules", []))

        def get_children(config, n = 0):
            # We need to remove any invalid configs because invalid configs
            # aren't saved but change detection assumes they were saved
            # Invalid configs aren't saved in cache with this
            children = [
                c for c in config.get("children", [])
                if validate_lobject(c, category_key_to_name, errors)
            ]
            n = set_order_information(children, n)

            lobjects_config = {str(c["key"]): c for c in children}
            config["children"] = set(lobjects_config.keys())

            for child in children:
                lobjects_config.update(get_children(child)[0])
            return lobjects_config, n

        # Get lobjects for each module, set lobject order information
        # and make a key -> module config mapping
        module_lobjects = {}
        modules_config = {}
        module_lobject_keys = {}
        nn = 0
        for m in config.get("modules", []):
            if "key" not in m:
                errors.append(_('COURSE_CONFIG_ERROR_MODULE_REQUIRES_KEY'))
                continue

            if not ("numerate_ignoring_modules" in config \
                    and parse_bool(config["numerate_ignoring_modules"])):
                nn = 0

            module_key = str(m["key"])
            module_lobjects[module_key], nn = get_children(m, nn)
            modules_config[module_key] = m
            module_lobject_keys[module_key] = set(module_lobjects[module_key].keys())

        config["categories"] = set(categories_config.keys())
        config["modules"] = set(modules_config.keys())

        return ConfigParts(
            config,
            categories_config,
            set(categories_config.keys()),
            {name: key for name, (key, _) in categories_config.items()},
            modules_config,
            set(modules_config.keys()),
            module_lobjects,
            module_lobject_keys,
        )

    @staticmethod
    def diff(old: Optional["ConfigParts"], new: "ConfigParts") -> "ConfigParts":
        """Return a new ConfigParts object containing the differences between the old and new configs"""
        if old is None:
            return new

        # Cannot be None due to keep_unchanged=True
        config = get_config_changes(
            old.config,
            new.config,
            keep=["publish_url", "errors", "build_log_url"],
            keep_unchanged=True
        )

        # Get the changes between the configs
        categories_config = get_config_changes(old.categories, new.categories)
        if categories_config is None:
            categories_config = {}

        modules_config = get_config_changes(old.modules, new.modules)
        if modules_config is None:
            modules_config = {}

        module_lobjects = get_config_changes(old.module_lobjects, new.module_lobjects, recurser=get_lobject_changes)
        if module_lobjects is None:
            module_lobjects = {}

        # Fully include all lobjects whose type has changed as they need to be remade
        for module in old.module_keys.intersection(new.module_keys):
            for lobject in old.module_lobject_keys[module].intersection(new.module_lobject_keys[module]):
                old_lobject = old.module_lobjects[module][lobject]
                new_lobject = new.module_lobjects[module][lobject]
                if lobject_class(old_lobject) != lobject_class(new_lobject):
                    module_lobjects[module][lobject] = new_lobject

        return ConfigParts(
            config,
            categories_config,
            new.category_names,
            new.category_key_map,
            modules_config,
            new.module_keys,
            module_lobjects,
            new.module_lobject_keys,
        )


def configure(instance: CourseInstance, new_config: dict) -> Tuple[bool, List[str]]: # noqa: MC0001
    new_config = copy.deepcopy(new_config)

    errors = []

    if "categories" not in new_config or not isinstance(new_config["categories"], dict):
        errors.append(_('COURSE_CONFIG_ERROR_CATEGORIES_REQUIRED_OBJECT'))
        return False, errors
    if "modules" not in new_config or not isinstance(new_config["modules"], list):
        errors.append(_('COURSE_CONFIG_ERROR_MODULES_REQUIRED_ARRAY'))
        return False, errors

    # Get the previous config (the one used in the last successful update)
    old_cparts = instance.get_cached_config()
    new_cparts = ConfigParts.from_config(new_config, errors)
    # Get the changes between the new config and the previous config with some auxiliary information.
    # See ConfigParts and ConfigParts.diff for more info
    cparts = ConfigParts.diff(old_cparts, new_cparts)

    config = cparts.config

    # wrap everything in a transaction to make sure invalid configuration isn't saved
    with transaction.atomic():
        # Configure course instance attributes.
        if "start" in config:
            dt = parse_date(config["start"], errors)
            if dt:
                instance.starting_time = dt
        if "end" in config:
            dt = parse_date(config["end"], errors)
            if dt:
                instance.ending_time = dt
        if "enrollment_start" in config:
            instance.enrollment_starting_time = parse_date(config["enrollment_start"], errors, allow_null=True)
        if "enrollment_end" in config:
            instance.enrollment_ending_time = parse_date(config["enrollment_end"], errors, allow_null=True)
        if "lifesupport_time" in config:
            instance.lifesupport_time = parse_date(config["lifesupport_time"], errors, allow_null=True)
        if "archive_time" in config:
            instance.archive_time = parse_date(config["archive_time"], errors, allow_null=True)
        if "enrollment_audience" in config:
            enroll_audience = parse_choices(config["enrollment_audience"], {
                    'internal': CourseInstance.ENROLLMENT_AUDIENCE.INTERNAL_USERS,
                    'external': CourseInstance.ENROLLMENT_AUDIENCE.EXTERNAL_USERS,
                    'all': CourseInstance.ENROLLMENT_AUDIENCE.ALL_USERS,
                }, "enrollment_audience", errors)
            if enroll_audience is not None:
                instance.enrollment_audience = enroll_audience
        if "view_content_to" in config:
            view_content_to = parse_choices(config["view_content_to"], {
                    'enrolled': CourseInstance.VIEW_ACCESS.ENROLLED,
                    'enrollment_audience': CourseInstance.VIEW_ACCESS.ENROLLMENT_AUDIENCE,
                    'all_registered': CourseInstance.VIEW_ACCESS.ALL_REGISTERED,
                    'public': CourseInstance.VIEW_ACCESS.PUBLIC,
                }, "view_content_to", errors)
            if view_content_to is not None:
                instance.view_content_to = view_content_to
        if "index_mode" in config:
            index_mode = parse_choices(config["index_mode"], {
                    'results': CourseInstance.INDEX_TYPE.RESULTS,
                    'toc': CourseInstance.INDEX_TYPE.TOC,
                    'last': CourseInstance.INDEX_TYPE.LAST,
                    'experimental': CourseInstance.INDEX_TYPE.EXPERIMENT,
                }, "index_mode", errors)
            if index_mode is not None:
                instance.index_mode = index_mode

        numbering_choices = {
            'none': CourseInstance.CONTENT_NUMBERING.NONE,
            'arabic': CourseInstance.CONTENT_NUMBERING.ARABIC,
            'roman': CourseInstance.CONTENT_NUMBERING.ROMAN,
            'hidden': CourseInstance.CONTENT_NUMBERING.HIDDEN,
        }
        if "content_numbering" in config:
            numbering = parse_choices(config["content_numbering"], numbering_choices,
                "content_numbering", errors)
            if numbering is not None:
                instance.content_numbering = numbering
        if "module_numbering" in config:
            numbering = parse_choices(config["module_numbering"], numbering_choices,
                "module_numbering", errors)
            if numbering is not None:
                instance.module_numbering = numbering
        if "course_description" in config:
            # Course index.yaml files have previously used the field "description"
            # for a hidden description, so we use "course_description" for
            # the visible description.
            instance.description = str(config["course_description"])
        if "course_footer" in config:
            instance.footer = str(config["course_footer"])
        if "lang" in config:
            langs = config["lang"]
            if isinstance(langs, list):
                langs = [lang for lang in langs if instance.is_valid_language(lang)]
                if langs:
                    instance.language = "|{}|".format("|".join(langs))
            elif instance.is_valid_language(langs):
                instance.language = str(langs)[:5]
        if "contact" in config:
            instance.technical_error_emails = str(config["contact"])
        if "head_urls" in config:
            head_urls = config["head_urls"]
            instance.head_urls = "\n".join(head_urls) if isinstance(head_urls, list) else str(head_urls)
        if "assistants" in config:
            if not isinstance(config["assistants"], list):
                errors.append(_('COURSE_CONFIG_ERROR_ASSISTANTS_AS_SID_ARRAY'))
            else:
                assistants = []
                for sid in config["assistants"]:
                    try:
                        profile = UserProfile.get_by_student_id(student_id=sid)
                    except UserProfile.DoesNotExist:
                        errors.append(
                            format_lazy(
                                _('COURSE_CONFIG_ERROR_ASSISTANT_NO_USER_WITH_SID -- {id}'),
                                id=sid,
                            )
                        )
                    else:
                        assistants.append(profile)
                instance.set_assistants(assistants)
        instance.build_log_url = str(config['build_log_url']) if 'build_log_url' in config else ''
        # configure_url excluded from validation because the default Django URL
        # validation does not accept dotless domain names such as "grader"
        instance.full_clean(exclude={'configure_url', 'build_log_url'})
        instance.save()

        old_categories = instance.categories.defer(None).all()

        # Create new categories
        new_category_names = cparts.categories.keys() - (c.name for c in old_categories)
        new_categories = [LearningObjectCategory(course_instance=instance, name=name) for name in new_category_names]

        # category key -> LearningObjectCategory object
        category_map = {
            cparts.category_key_map[category.name]: category
            for category in list(old_categories) + new_categories
            if category.name in cparts.category_names
        }

        # Configure learning object categories.
        for category in list(old_categories) + new_categories:
            if category.name not in cparts.category_names:
                category.status = LearningObjectCategory.STATUS.HIDDEN
                category.save()
                continue

            # Skip unchanged categories
            if category.name not in cparts.categories:
                continue

            key, c = cparts.categories[category.name]

            if "status" in c:
                category.status = str(c["status"])
            if "description" in c:
                category.description = str(c["description"])
            if "points_to_pass" in c:
                i = parse_int(c["points_to_pass"], errors)
                if i is not None:
                    category.points_to_pass = i
            for field in [
                "confirm_the_level",
                "accept_unofficial_submits",
            ]:
                if field in c:
                    setattr(category, field, parse_bool(c[field]))
            category.full_clean()
            category.save()

        old_modules = instance.course_modules.defer(None).all()

        # Create new modules
        new_module_keys = cparts.modules.keys() - (c.url for c in old_modules)
        new_modules = [CourseModule(course_instance=instance, url=key) for key in new_module_keys]
        # bulk_create doesn't get generated primary keys, so we need to save them individually
        for module in new_modules:
            module.save()

        # Update the learning objects within each of the new and old modules
        for module in list(old_modules) + new_modules:
            # TODO: test if doing defer(None) only on the lobjects that
            # will be modified is a significant improvement
            old_lobjects = module.learning_objects.defer(None).all()
            old_lobject_keys = {c.url for c in old_lobjects}
            lobject_map = {obj.url: obj for obj in old_lobjects}

            # Keys of lobjects to be deleted/hidden (i.e. lobjects not present in new version)
            outdated_lobjects = [
                lobject_map[key]
                for key in old_lobject_keys - cparts.module_lobject_keys.get(module.url, set())
            ]
            # Only update changed learning objects
            if module.url in cparts.module_lobjects:
                lobjects_config = cparts.module_lobjects[module.url]

                # Check and update exercise object types if they have changed
                for key, lobject_config in lobjects_config.items():
                    # Select exercise class.
                    lobject_cls = lobject_class(lobject_config)

                    if key in old_lobject_keys:
                        lobject = lobject_map[key]

                        # We cannot use isinstance as LTIExercise inherits BaseExercise
                        if not type(lobject) is lobject_cls: # pylint: disable=unidiomatic-typecheck
                            outdated_lobjects.append(lobject)

                            lobject.url = lobject.url + "_old"
                            lobject.save()
                            lobject_map[key] = lobject_cls(course_module=module, url=key)
                    else:
                        lobject_map[key] = lobject_cls(course_module=module, url=key)

                update_learning_objects(
                    category_map,
                    lobjects_config,
                    lobject_map,
                    errors,
                )

                # We can't set the children until they have been saved by update_learning_objects
                for key, lobject_config in lobjects_config.items():
                    lobject_map[key].children.set(
                        lobject_map[child_key]
                        for child_key in lobject_config["children"]
                    )

            # Delete or hide learning objects that are not included in the module anymore
            for lobject in outdated_lobjects:
                if (
                    not isinstance(lobject, BaseExercise)
                    or not lobject.submissions.exists()
                ):
                    lobject.delete()
                else:
                    lobject.status = LearningObject.STATUS.HIDDEN
                    lobject.order = 9999
                    # .parent may have been deleted: only save status and order
                    lobject.save(update_fields=["status", "order"])

        # Update the modules
        for module in list(old_modules) + new_modules:
            #  Delete/hide any old modules not present in new version
            if module.url not in cparts.module_keys:
                if not module.learning_objects.exists():
                    module.delete()
                else:
                    module.status = CourseModule.STATUS.HIDDEN
                    module.save()

                continue

            # Skip unchanged modules
            if module.url not in cparts.modules:
                continue

            m = cparts.modules[module.url]

            if "order" in m:
                module.order = parse_int(m["order"], errors)

            if "title" in m:
                module.name = format_localization(m["title"])
            elif "name" in m:
                module.name = format_localization(m["name"])
            if not module.name:
                module.name = "-"
            if "status" in m:
                module.status = str(m["status"])
            if "points_to_pass" in m:
                i = parse_int(m["points_to_pass"], errors)
                if i is not None:
                    module.points_to_pass = i
            if "introduction" in m:
                module.introduction = str(m["introduction"])

            if "open" in m:
                dt = parse_date(m["open"], errors)
                if dt:
                    module.opening_time = dt
            if not module.opening_time:
                module.opening_time = instance.starting_time

            if "close" in m:
                dt = parse_date(m["close"], errors)
                if dt:
                    module.closing_time = dt
            elif "duration" in m:
                dt = parse_duration(module.opening_time, m["duration"], errors)
                if dt:
                    module.closing_time = dt
            if not module.closing_time:
                module.closing_time = instance.ending_time

            if "read-open" in m:
                module.reading_opening_time = parse_date(m["read-open"], errors, allow_null=True)

            if "late_close" in m:
                dt = parse_date(m["late_close"], errors)
                if dt:
                    module.late_submission_deadline = dt
                    module.late_submissions_allowed = True
            elif "late_duration" in m:
                dt = parse_duration(module.closing_time, m["late_duration"], errors)
                if dt:
                    module.late_submission_deadline = dt
                    module.late_submissions_allowed = True
            if "late_penalty" in m:
                f = parse_float(m["late_penalty"], errors)
                if f is not None:
                    module.late_submission_penalty = f

            module.full_clean()
            module.save()

        # Clean up obsolete categories.
        for category in instance.categories.filter(status=LearningObjectCategory.STATUS.HIDDEN):
            if not category.learning_objects.exists():
                category.delete()

        if "publish_url" in config:
            success = False
            publish_errors = []
            try:
                permissions = Permissions()
                permissions.instances.add(Permission.READ, id=instance.id)
                permissions.instances.add(Permission.WRITE, id=instance.id)
                response = aplus_get(config["publish_url"], permissions=permissions)
            except ConnectionError as e:
                publish_errors = [str(e)]
            else:
                if response.status_code != 200:
                    publish_errors = [format_lazy(
                        _("PUBLISH_RESPONSE_NON_200 -- {status_code}"),
                        status_code=response.status_code
                    )]

                if response.text:
                    try:
                        publish_errors = json.loads(response.text)
                    except Exception as e:
                        publish_errors = [format_lazy(
                            _("PUBLISH_ERROR_JSON_PARSER_FAILED -- {e}, {text}"),
                            e=e,
                            text=response.text
                        )]
                    else:
                        if isinstance(publish_errors, dict):
                            success = publish_errors.get("success", True)
                            publish_errors = publish_errors.get("errors", [])

                        if isinstance(publish_errors, list):
                            publish_errors = [str(e) for e in publish_errors]
                        else:
                            publish_errors = [str(publish_errors)]

            if publish_errors:
                if not success:
                    errors.append(format_lazy(
                        _("PUBLISHED_WITH_ERRORS -- {publish_url}"),
                        publish_url=config['publish_url']
                    ))
                errors.extend(str(e) for e in publish_errors)

            if not success:
                transaction.set_rollback(True)
                return False, errors

    # We only save the config in cache if the update was successful (i.e. changes were committed to database)
    instance.set_cached_config(new_cparts)

    return True, errors


def configure_from_url(instance: CourseInstance, url: str) -> Tuple[bool, List[str]]:
    """
    Configures course content by trusted remote URL.
    """
    if not url:
        return False, [_('COURSE_CONFIG_URL_REQUIRED')]

    # save the url before fetching config. The JWT system requires this to be
    # set, so that A+ knows which service to trust to have access to the course
    # instance. The aplus config url might need access to the course instance.
    # The other service might also need to have access to the course instance
    # before it can be configured from the url.
    instance.configure_url = url
    instance.save()

    try:
        url = url.strip()
        permissions = Permissions()
        permissions.instances.add(Permission.READ, id=instance.id)
        permissions.instances.add(Permission.WRITE, id=instance.id)
        response = aplus_get(url, permissions=permissions)
        response.raise_for_status()
    except Exception as e:
        return False, [format_lazy(
            _('COURSE_CONFIG_ERROR_REQUEST_FAILED -- {error!s}'),
            error=e,
        )]

    try:
        config = json.loads(response.text)
    except Exception as e:
        return False, [format_lazy(
            _('COURSE_CONFIG_ERROR_JSON_PARSER_FAILED -- {error!s}'),
            error=e,
        )]

    if not isinstance(config, dict):
        return False, [_("COURSE_CONFIG_ERROR_INVALID_JSON")]

    errors = config.pop('errors', [])
    if not isinstance(errors, list):
        errors = [str(errors)]

    if not config.pop('success', True):
        errors.insert(0, _("COURSE_CONFIG_ERROR_SERVICE_FAILED_TO_EXPORT"))
        return False, errors

    status, configure_errors = configure(instance, config)

    return status, errors + configure_errors
