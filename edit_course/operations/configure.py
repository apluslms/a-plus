import json
import requests
from datetime import datetime, timedelta
from django.utils import timezone
from django.utils.translation import ugettext_lazy as _

from exercise.models import LearningObject, CourseChapter, BaseExercise, LTIExercise
from external_services.models import LTIService
from userprofile.models import UserProfile


def parse_date(value, errors):
    for fmt in ['%Y-%m-%dT%H:%M:%SZ','%Y-%m-%dT%H:%M:%S','%Y-%m-%d %H:%M:%S',
        '%Y-%m-%d %H:%M','%Y-%m-%d %H','%Y-%m-%d']:
        try:
            return timezone.make_aware(datetime.strptime(str(value), fmt),
                timezone.get_current_timezone())
        except ValueError:
            pass
    errors.append(_("Unable to parse date: {}").format(value))
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
    errors.append(_("Unable to parse duration: {}").format(value))
    return None


def parse_int(value, errors):
    try:
        return int(value)
    except ValueError:
        errors.append(_("Unable to parse int: {}").format(value))
    return None


def parse_float(value, errors):
    try:
        return float(value)
    except ValueError:
        errors.append(_("Unable to parse float: {}").format(value))
    return None


def parse_bool(value):
    return value in [True, "true", "yes", "True", "Yes"]


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
            errors.append(_("Unknown category {}").format(o["category"]))
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
            if not lti is None:
                lobject.lti_service = lti
            for key in [
                "context_id",
                "resource_link_id",
            ]:
                obj_key = "lti_" + key
                if obj_key in o:
                    setattr(lobject, key, o[obj_key])
            lobject.aplus_get_and_post = o.get("lti_aplus_get_and_post", True)

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

        if "order" in o:
            lobject.order = parse_int(o["order"], errors)
        else:
            n += 1
            lobject.order = n
        if "url" in o:
            lobject.service_url = str(o["url"])
        if "status" in o:
            lobject.status = str(o["status"])[:32]
        if "audience" in o:
            words = { 'internal':1, 'external':2, 'registered':3 }
            lobject.audience = words.get(o['audience'], 0)
        if "title" in o:
            lobject.name = str(o["title"])
        elif "name" in o:
            lobject.name = str(o["name"])
        if not lobject.name:
            lobject.name = "-"
        if "description" in o:
            lobject.description = str(o["description"])
        if "use_wide_column" in o:
            lobject.use_wide_column = parse_bool(o["use_wide_column"])
        if "exercise_info" in o:
            lobject.exercise_info = o["exercise_info"]
        if "model_answer" in o:
            lobject.model_answers = o["model_answer"]
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
        return {'error': _("Requesting build log failed: {}").format(str(e))}
    try:
        data = json.loads(response.text)
    except Exception as e:
        return {'error': _("Failed to parse the build log JSON: {}").format(str(e))}
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
        return [_("Request failed: {}").format(str(e))]

    instance.configure_url = url
    instance.save()

    try:
        config = json.loads(response.text)
    except Exception as e:
        return [_("Failed to parse the JSON: {}").format(str(e))]

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
    if "lang" in config:
        instance.language = str(config["lang"])[:5]
    if "contact" in config:
        instance.technical_error_emails = str(config["contact"])
    if "assistants" in config:
        if not isinstance(config["assistants"], list):
            errors.append(_("Assistants must be given as student ID array."))
        else:
            try:
                profiles = [UserProfile.objects.get(student_id=sid)
                    for sid in config["assistants"]]
                instance.assistants = profiles
            except UserProfile.DoesNotExist as err:
                errors.append(_("Assistant student ID was not found: {}")\
                    .format(str(err)))
    if "build_log_url" in config:
        instance.build_log_url = str(config["build_log_url"])
    instance.save()

    if not "categories" in config or not isinstance(config["categories"], dict):
        errors.append(_("Categories required as object."))
        return errors
    if not "modules" in config or not isinstance(config["modules"], list):
        errors.append(_("Modules required as array."))
        return errors

    # Configure learning object categories.
    category_map = {}
    seen = []
    for key, c in config.get("categories", {}).items():
        if not "name" in c:
            errors.append(_("Category requires a name."))
            continue
        category, flag = instance.categories.get_or_create(name=str(c["name"]))
        if "status" in c:
            category.status = str(c["status"])[:32]
        if "description" in c:
            category.description = str(c["description"])
        if "points_to_pass" in c:
            i = parse_int(c["points_to_pass"], errors)
            if not i is None:
                category.points_to_pass = i
        for key in [
            "confirm_the_level",
            "accept_unofficial_submits",
        ]:
            if key in c:
                setattr(category, key, parse_bool(o[key]))
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
        module, flag = instance.course_modules.get_or_create(url=str(m["key"]))

        if "order" in m:
            module.order = parse_int(m["order"], errors)
        else:
            n += 1
            module.order = n

        if "title" in m:
            module.name = str(m["title"])
        elif "name" in m:
            module.name = str(m["name"])
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
                    lobject.delete()
                else:
                    lobject.status = "hidden"
                    lobject.order = 9999
                    lobject.save()

    # Clean up obsolete categories.
    for category in instance.categories.filter(status="hidden"):
        if category.learning_objects.count() == 0:
            category.delete()

    return errors
