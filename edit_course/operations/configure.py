import json
import requests
from datetime import datetime, timedelta
from django.utils import timezone
from django.utils.translation import ugettext_lazy as _

from exercise.models import CourseChapter, BaseExercise
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
                return timezone.make_aware(datetime(begin.year, begin.month + i,
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
        return start
    for o in config:
        n += 1
        if not "key" in o:
            errors.append(_("Learning object requires a key."))
            continue
        if not "url" in o:
            errors.append(_("Learning object requires an url."))
            continue
        if not "category" in o:
            errors.append(_("Learning object requires a category."))
            continue
        if not o["category"] in category_map:
            errors.append(_("Unknown category {}").format(o["category"]))
            continue

        # Select exercise class.
        if "points_to_pass" in o:
            lobject = BaseExercise.objects.filter(
                course_module__course_instance=module.course_instance,
                service_url=str(o["url"])).first()
            if lobject:
                lobject.course_module = module
            else:
                lobject = BaseExercise(course_module=module,
                    service_url=str(o["url"]))
            if "allow_assistant_grading" in o:
                lobject.allow_assistant_grading = parse_bool(
                    o["allow_assistant_grading"])
            for key in ["min_group_size", "max_group_size", "max_submissions",
                "max_points", "points_to_pass"]:
                if key in o:
                    i = parse_int(o[key], errors)
                    if not i is None:
                        setattr(lobject, key, i)
        else:
            lobject = CourseChapter.objects.filter(
                course_module__course_instance=module.course_instance,
                service_url=str(o["url"])).first()
            if lobject:
                lobject.course_module=module
            else:
                lobject = CourseChapter(course_module=module,
                    service_url=str(o["url"]))
            if "generate_table_of_contents" in o:
                lobject.generate_table_of_contents = parse_bool(
                    o["generate_table_of_contents"])

        lobject.category = category_map[o["category"]]
        lobject.parent = parent
        lobject.url = str(o["key"])
        lobject.order = n
        if "status" in o:
            lobject.status = str(o["status"])[:32]
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
        lobject.save()
        seen.append(lobject.id)
        if "children" in o:
            configure_learning_objects(category_map, module, o["children"],
                lobject, seen, errors)
    return n

def configure_content(instance, url):
    """
    Configures course content by trusted remote URL.
    """
    if not url:
        return [_("Configuration URL required.")]
    try:
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
        n += 1
        if not "key" in m:
            errors.append(_("Module requires a key."))
            continue
        module, flag = instance.course_modules.get_or_create(url=str(m["key"]))
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
            print(nn, m['name'])
            nn = configure_learning_objects(category_map, module, m["children"],
                None, seen_objects, errors, nn)

    for module in instance.course_modules.all():
        if not module.id in seen_modules:
            module.status = "hidden"
            module.save()
        for lobject in module.learning_objects.all():
            if not lobject.id in seen_objects:
                lobject.status = "hidden"
                lobject.save()

    # Clean up obsolete categories.
    for category in instance.categories.filter(status="hidden"):
        if category.learning_objects.count() == 0:
            category.delete()

    return errors
