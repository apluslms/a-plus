import json
import requests
from datetime import datetime, timedelta
from django.utils import timezone
from django.utils.translation import ugettext_lazy as _

from exercise.models import LearningObject, CourseChapter, BaseExercise, LTIExercise
from external_services.models import LTIService
from userprofile.models import UserProfile
from lib.localization_syntax import format_localization

from exercise.exercisecollection_models import ExerciseCollection
from course.models import Course, CourseInstance, CourseModule, LearningObjectCategory
from django.core.exceptions import ObjectDoesNotExist
from aplus import settings


def parse_date(value, errors):
    for fmt in ['%Y-%m-%dT%H:%M:%SZ','%Y-%m-%dT%H:%M:%S','%Y-%m-%d %H:%M:%S',
        '%Y-%m-%d %H:%M','%Y-%m-%d %H','%Y-%m-%d']:
        try:
            return timezone.make_aware(datetime.strptime(str(value), fmt),
                timezone.get_current_timezone())
        except ValueError:
            pass
    errors.append(_("Unable to parse value '{value}' as a date.").format(value=value))
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
    errors.append(_("Unable to parse value '{value}' as a time duration.").format(value=value))
    return None


def parse_int(value, errors):
    try:
        return int(value)
    except ValueError:
        errors.append(_("Unable to parse value '{value}' as an int.").format(value=value))
    return None


def parse_float(value, errors):
    try:
        return float(value)
    except ValueError:
        errors.append(_("Unable to parse value '{value}' as a float.").format(value=value))
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
        errors.append(_("Field '{field}' has an unknown value '{value}'.").format(
                field=field_name, value=str(value)))
        return None
    return parsed_value


def configure_learning_objects(category_map, module, config, parent,
        seen, errors, n=0):
    if not isinstance(config, list):
        return n
    for o in config:
        if not "key" in o:
            errors.append(_("Learning object requires a key."))
            continue
        if not "category" in o:
            errors.append(_("Learning object requires a category."))
            continue
        if not o["category"] in category_map:
            errors.append(_("Unknown category '{category}'.").format(category=o["category"]))
            continue

        lobject = LearningObject.objects.filter(
            #course_module__course_instance=module.course_instance,
            course_module=module,
            url=str(o["key"])
        ).first()
        if not lobject is None:
            lobject = lobject.as_leaf_class()

        # Select exercise class.
        lobject_cls = (
            LTIExercise if "lti" in o
            else ExerciseCollection if "collection_category" in o
            else BaseExercise if "max_submissions" in o
            else CourseChapter
        )

        if not lobject is None and not isinstance(lobject, lobject_cls):
            lobject.url = lobject.url + "_old"
            lobject.save()
            lobject = None
        if lobject is None:
            lobject = lobject_cls(course_module=module, url=str(o["key"]))

        if lobject_cls == LTIExercise:
            lti = LTIService.objects.filter(menu_label=str(o["lti"])).first()
            if lti is None:
                errors.append(
                    _("The site has no configuration for the LTI service '{lti_label}' "
                    "used by the LTI exercise '{exercise_key}'. You may have misspelled "
                    "the value for the field 'lti' or the site administrator has not yet "
                    "added the configuration for the LTI service. The exercise was not "
                    "created/updated due to the error.")
                    .format(lti_label=str(o["lti"]), exercise_key=str(o["key"]))
                )
                if hasattr(lobject, 'id'):
                    # Avoid deleting LTI exercises from A+ since the LTI parameters
                    # may have been used with an external tool.
                    seen.append(lobject.id)
                # The learning object can not be saved without an LTI service
                # since the foreign key is required.
                continue
            else:
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
                    if not i is None:
                        setattr(lobject, key, i)
            if "difficulty" in o:
                lobject.difficulty = o["difficulty"]

        if lobject_cls == CourseChapter:
            if "generate_table_of_contents" in o:
                lobject.generate_table_of_contents = parse_bool(
                    o["generate_table_of_contents"])

        lobject.category = category_map[o["category"]]
        lobject.parent = parent

        if lobject_cls == ExerciseCollection:
            if 'collection_course' in o and not o['collection_course'] is None:
                target_category, error_msg = get_target_category(o["collection_category"],
                                                                 course=o["collection_course"],)
            else:
                target_category, error_msg = get_target_category(o["collection_category"],
                                                                 course_url=o["collection_url"], )
            if error_msg:
                errors.append("{} | {}".format(o["key"], error_msg))
                continue

            if target_category.id == lobject.category.id:
                errors.append("ExerciseCollection can't target its own category")
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
            lobject.status = str(o["status"])[:32]
        if "audience" in o:
            words = { 'internal':1, 'external':2, 'registered':3 }
            lobject.audience = words.get(o['audience'], 0)
        if "title" in o:
            lobject.name = format_localization(o["title"])
        elif "name" in o:
            lobject.name = format_localization(o["name"])
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
        return {'error': _("Cannot request build log from build_log_url when it is blank.")}
    try:
        response = requests.get(instance.build_log_url)
    except Exception as e:
        return {'error': _("Requesting build log failed with error '{error!s}'.")\
                .format(error=e)}
    try:
        data = json.loads(response.text)
    except Exception as e:
        return {'error': _("Parsing the build log JSON raised error '{error!s}'.")\
                .format(error=e)}
    if not data:
        return {'error': _("Remote URL returned an empty build log.")}
    return data


def configure_content(instance, url):
    """
    Configures course content by trusted remote URL.
    """
    if not url:
        return [_("Configuration URL required.")]
    try:
        url = url.strip()
        response = requests.get(url)
    except Exception as e:
        return [_("Request for a course configuration failed with error '{error!s}'. "
                  "Configuration of course aborted.").format(error=e)]

    instance.configure_url = url
    instance.save()

    try:
        config = json.loads(response.text)
    except Exception as e:
        return [_("JSON parser raised error '{error!s}'. "
                  "Configuration of course aborted.").format(error=e)]

    errors = []

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
        dt = parse_date(config["enrollment_start"], errors)
        if dt:
            instance.enrollment_starting_time = dt
    if "enrollment_end" in config:
        dt = parse_date(config["enrollment_end"], errors)
        if dt:
            instance.enrollment_ending_time = dt
    if "lifesupport_time" in config:
        dt = parse_date(config["lifesupport_time"], errors)
        if dt:
            instance.lifesupport_time = dt
    if "archive_time" in config:
        dt = parse_date(config["archive_time"], errors)
        if dt:
            instance.archive_time = dt
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
            errors.append(_("Assistants must be given as a student ID array."))
        else:
            assistants = []
            for sid in config["assistants"]:
                try:
                    profile = UserProfile.objects.get(student_id=sid)
                except UserProfile.DoesNotExist as err:
                    errors.append(_("Adding the assistant failed, because an associated "
                                    "user with student ID {id} does not exist.").format(id=sid))
                else:
                    assistants.append(profile)
            instance.assistants.set(assistants)
    if "build_log_url" in config:
        instance.build_log_url = str(config["build_log_url"])
    # configure_url excluded from validation because the default Django URL
    # validation does not accept dotless domain names such as "grader"
    instance.full_clean(exclude=['configure_url'])
    instance.save()

    if not "categories" in config or not isinstance(config["categories"], dict):
        errors.append(_("Categories required as an object."))
        return errors
    if not "modules" in config or not isinstance(config["modules"], list):
        errors.append(_("Modules required as an array."))
        return errors

    # Configure learning object categories.
    category_map = {}
    seen = []
    for key, c in config.get("categories", {}).items():
        if not "name" in c:
            errors.append(_("Category requires a name."))
            continue
        try:
            category = instance.categories.get(name=format_localization(c["name"]))
        except LearningObjectCategory.DoesNotExist:
            category = LearningObjectCategory(course_instance=instance,
                name=format_localization(c["name"]))
        if "status" in c:
            category.status = str(c["status"])[:32]
        if "description" in c:
            category.description = str(c["description"])
        if "points_to_pass" in c:
            i = parse_int(c["points_to_pass"], errors)
            if not i is None:
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
        if not category.id in seen:
            category.status = 'hidden'
            category.save()

    # Configure course modules.
    seen_modules = []
    seen_objects = []
    nn = 0
    n = 0
    for m in config.get("modules", []):
        if not "key" in m:
            errors.append(_("Module requires a key."))
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
            module.status = str(m["status"])[:32]
        if "points_to_pass" in m:
            i = parse_int(m["points_to_pass"], errors)
            if not i is None:
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
            if not f is None:
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

    for module in list(instance.course_modules.all()):
        if not module.id in seen_modules:
            module.status = "hidden"
            module.save()
        for lobject in list(module.learning_objects.all()):
            if not lobject.id in seen_objects:
                exercise = lobject.as_leaf_class()
                if (
                    not isinstance(exercise, BaseExercise)
                    or exercise.submissions.count() == 0
                ):
                    exercise.delete()
                else:
                    lobject.status = "hidden"
                    lobject.order = 9999
                    lobject.save()

    # Clean up obsolete categories.
    for category in instance.categories.filter(status="hidden"):
        if category.learning_objects.count() == 0:
            category.delete()

    return errors

def get_target_category(category, course=None, course_url=None):

    course_name = None
    instance_name = None


    if not category:
        return None, _("ExerciseCollection object requires collection_category.")

    if (course or course_url) and not (course and course_url):
        return None, _("ExerciseCollection object must have either identified or URL")

    if course:
        course_name, instance_name = course.split(";")

        try:
            Course.objects.get(name=course_name)
        except:
            return None, _('Course: {} does not exist'.format(course_name))

        try:
            course_instance = CourseInstance.objects.get(instance_name=instance_name,
                                                         course__name=course_name)
        except ObjectDoesNotExist:
            return None, _("Course: {}, Instance: {}, not found.".format(course_name, instance_name))

    else:
        course_slug_begin = 0
        if not settings.BASE_URL in course_url:
            return None, _('ExerciseColletion URL "{}" not in correct domain {}.'.format(course_url,settings.BASE_URL))

        course_slug_begin = len(settings.BASE_URL)
        instance_slug_begin = course_url.find('/', course_slug_begin) + 1
        course_slug = course_url[course_slug_begin : instance_slug_begin - 1]
        instance_slug = course_url[instance_slug_begin: course_url.find('/', instance_slug_begin)]
        
        try:
            course_instance = CourseInstance.objects.get(url=instance_slug,
                                                         course__url=course_slug)
        except ObjectDoesNotExist:
            return None, _('No course found with URL "{}"'.format(course_url))


    try:
        target_category = course_instance.categories.get(name=category)
    except ObjectDoesNotExist:
        return None, _("Category: {}, not found in Course: {}, Instance: {}.".format(
            category, course_name, instance_name))

    return target_category, None
