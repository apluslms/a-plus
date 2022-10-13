import json
from datetime import datetime, timedelta
from urllib.parse import urlparse
from typing import Any, Dict, List, Optional, Tuple

from aplus_auth.payload import Permission, Permissions
from aplus_auth.requests import get as aplus_get
from django.db import transaction
from django.conf import settings
from django.core.exceptions import ObjectDoesNotExist
from django.utils import timezone
from django.utils.text import format_lazy
from django.utils.translation import gettext_lazy as _

from course.models import CourseInstance, CourseModule, LearningObjectCategory
from exercise.exercisecollection_models import ExerciseCollection
from exercise.models import LearningObject, CourseChapter, BaseExercise, LTIExercise, RevealRule
from external_services.models import LTIService
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


def configure_learning_objects( # noqa: MC0001
        category_map: Dict[str, LearningObjectCategory],
        module: CourseModule,
        config: List[Dict[str, Any]],
        parent: Optional[LearningObject],
        seen: List[int],
        errors: List[str],
        n: int = 0,
        ) -> int:
    if not isinstance(config, list):
        return n
    for o in config:
        if "key" not in o:
            errors.append(_('LEARNING_OBJECT_ERROR_REQUIRES_KEY'))
            continue
        if "category" not in o:
            errors.append(_('LEARNING_OBJECT_ERROR_REQUIRES_CATEGORY'))
            continue
        if not o["category"] in category_map:
            errors.append(
                format_lazy(
                    _('LEARNING_OBJECT_ERROR_UNKNOWN_CATEGORY -- {category}'),
                    category=o["category"],
                )
            )
            continue

        lobject = LearningObject.objects.filter(
            #course_module__course_instance=module.course_instance,
            course_module=module,
            url=str(o["key"])
        ).defer(None).first()

        # Select exercise class.
        lobject_cls = (
            LTIExercise if "lti" in o
            else ExerciseCollection if "target_category" in o
            else BaseExercise if "max_submissions" in o
            else CourseChapter
        )

        if lobject is not None and not isinstance(lobject, lobject_cls):
            lobject.url = lobject.url + "_old"
            lobject.save()
            lobject = None
        if lobject is None:
            lobject = lobject_cls(course_module=module, url=str(o["key"]))

        if lobject_cls == LTIExercise:
            lti = LTIService.objects.filter(menu_label=str(o["lti"])).first()
            if lti is None:
                errors.append(
                    format_lazy(
                        _('LTI_ERROR_NO_CONFIGURATION_TO_SERVICE_USED_BY_EXERCISE -- {lti_label}, {exercise_key}'),
                        lti_label=str(o["lti"]),
                        exercise_key=str(o["key"]),
                    )
                )
                if hasattr(lobject, 'id'):
                    # Avoid deleting LTI exercises from A+ since the LTI parameters
                    # may have been used with an external tool.
                    seen.append(lobject.id)
                # The learning object can not be saved without an LTI service
                # since the foreign key is required.
                continue
            lobject.lti_service = lti
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

        if lobject_cls in (LTIExercise, BaseExercise):
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
        lobject.parent = parent

        if lobject_cls == ExerciseCollection:
            target_category, error_msg = get_target_category(o["target_category"],
                                                             o["target_url"],)
            if error_msg:
                errors.append("{} | {}".format(o["key"], error_msg))
                continue

            if target_category.id == lobject.category.id:
                errors.append("{} | ExerciseCollection can't target its own category".format(o["key"]))
                continue

            for key in [
                "min_group_size",
                "max_group_size",
                "max_submissions",
            ]:
                if key in o:
                    errors.append("Can't define '{}' for ExerciseCollection".format(key))

            if "max_points" in o and o["max_points"] <= 0:
                errors.append("ExerciseCollection can't have max_points <= 0")
                continue

            lobject.max_points = o['max_points']
            lobject.points_to_pass = o['points_to_pass']

            lobject.target_category = target_category
            lobject.min_group_size = 1
            lobject.max_group_size = 1
            lobject.max_submissions = 1

        if "order" in o:
            lobject.order = parse_int(o["order"], errors)
        else:
            n += 1
            lobject.order = n
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
        seen.append(lobject.id)
        if "children" in o:
            configure_learning_objects(category_map, module, o["children"],
                lobject, seen, errors)
    return n


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


def configure_content(instance: CourseInstance, url: str) -> Tuple[bool, List[str]]: # noqa: MC0001
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

    errors = config.get('errors', [])
    if not isinstance(errors, list):
        errors = [str(errors)]

    if not config.get('success', True):
        errors.insert(0, _("COURSE_CONFIG_ERROR_SERVICE_FAILED_TO_EXPORT"))
        return False, errors

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
                    except UserProfile.DoesNotExist as err: # noqa: F841
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
        instance.full_clean(exclude=['configure_url', 'build_log_url'])
        instance.save()

        if "categories" not in config or not isinstance(config["categories"], dict):
            errors.append(_('COURSE_CONFIG_ERROR_CATEGORIES_REQUIRED_OBJECT'))
            transaction.set_rollback(True)
            return False, errors
        if "modules" not in config or not isinstance(config["modules"], list):
            errors.append(_('COURSE_CONFIG_ERROR_MODULES_REQUIRED_ARRAY'))
            transaction.set_rollback(True)
            return False, errors

        # Configure learning object categories.
        category_map = {}
        seen = []
        for key, c in config.get("categories", {}).items():
            if "name" not in c:
                errors.append(_('COURSE_CONFIG_ERROR_CATEGORY_REQUIRES_NAME'))
                continue
            try:
                category = instance.categories.get(name=format_localization(c["name"]))
            except LearningObjectCategory.DoesNotExist:
                category = LearningObjectCategory(course_instance=instance,
                    name=format_localization(c["name"]))
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
            category_map[key] = category
            seen.append(category.id)

        for category in instance.categories.all():
            if category.id not in seen:
                category.status = LearningObjectCategory.STATUS.HIDDEN
                category.save()

        # Configure course modules.
        seen_modules = []
        seen_objects = []
        nn = 0
        n = 0
        for m in config.get("modules", []):
            if "key" not in m:
                errors.append(_('COURSE_CONFIG_ERROR_MODULE_REQUIRES_KEY'))
                continue
            try:
                module = instance.course_modules.get(url=str(m["key"]))
            except CourseModule.DoesNotExist:
                module = CourseModule(course_instance=instance, url=str(m["key"]))

            if "order" in m:
                module.order = parse_int(m["order"], errors)
            else:
                n += 1
                module.order = n

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
            seen_modules.append(module.id)

            if not ("numerate_ignoring_modules" in config \
                    and parse_bool(config["numerate_ignoring_modules"])):
                nn = 0
            if "children" in m:
                nn = configure_learning_objects(category_map, module, m["children"],
                    None, seen_objects, errors, nn)

        for module in instance.course_modules.all():
            # cache invalidation uses the parent when learning object is saved:
            # prefetch parent so that it wont be fetched after the it was deleted
            for lobject in module.learning_objects.all():
                if lobject.id not in seen_objects:
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
            if module.id not in seen_modules:
                if not module.learning_objects.exists():
                    module.delete()
                else:
                    module.status = CourseModule.STATUS.HIDDEN
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
                            publish_errors = (str(e) for e in publish_errors)
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

    return True, errors


def get_target_category(category, course_url):

    if not category:
        return None, _('COURSE_CONFIG_ERROR_EXERCISECOLLECTION_REQUIRES_CATEGORY')

    if not course_url:
        return None, _('COURSE_CONFIG_ERROR_EXERCISECOLLECTION_REQUIRES_INSTANCE_URL')

    parsed_url = urlparse(course_url)
    service_hostname = urlparse(settings.BASE_URL).hostname

    if parsed_url.hostname != service_hostname:
        return None, format_lazy(
            _('COURSE_CONFIG_ERROR_COURSE_URL_SHOULD_MATCH_SERVICE -- {}, {}'),
            course_url,
            service_hostname
        )

    try:
        course_slug, instance_slug = parsed_url.path.split('/')[1:3]
    except ValueError:
        return None, format_lazy(
            _('COURSE_CONFIG_ERROR_DETERMINING_COURSE_OR_INSTANCE_FROM_URL_FAILED -- {}'),
            course_url
        )

    try:
        course_instance = CourseInstance.objects.get(url=instance_slug,
                                                     course__url=course_slug)
    except ObjectDoesNotExist:
        return None, format_lazy(_('COURSE_CONFIG_ERROR_NO_COURSE_FOUND -- {}, {}, {}'),
            course_url, course_slug, instance_slug)

    try:
        target_category = course_instance.categories.get(name=category)
    except ObjectDoesNotExist:
        return None, format_lazy(_('COURSE_CONFIG_ERROR_CATEGORY_NOT_FOUND_IN_COURSE -- {}'),
            category)

    return target_category, None
