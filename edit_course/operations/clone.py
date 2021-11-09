import logging

from exercise.exercise_models import BaseExercise, CourseChapter
from django.db import transaction
from django.contrib.auth.models import User
from course.models import CourseInstance
from course.sis import get_sis_configuration, StudentInfoSystem

logger = logging.getLogger("aplus.course")

def clone_learning_objects(
        category_map,
        module,
        objects,
        parent,
        clone_chapters,
        clone_exercises,
):
    """
    Clones learning objects recursively.
    """
    for lobject in list(a.as_leaf_class() for a in objects):
        children = list(lobject.children.all())

        # The user can choose to import just chapters or just exercises. If
        # this learning object is not of a requested type, skip it and reparent
        # its children.
        cloned = False
        if (
            (isinstance(lobject, CourseChapter) and clone_chapters) or
            (isinstance(lobject, BaseExercise) and clone_exercises)
        ):
            # Save as new learning object.
            lobject.id = None
            lobject.modelwithinheritance_ptr_id = None
            if hasattr(lobject, "learningobject_ptr_id"):
                lobject.learningobject_ptr_id = None
            if hasattr(lobject, "baseexercise_ptr_id"):
                lobject.baseexercise_ptr_id = None
            lobject.category = category_map[lobject.category.id]
            lobject.course_module = module
            lobject.parent = parent
            lobject.save()
            cloned = True

        clone_learning_objects(
            category_map,
            module,
            children,
            lobject if cloned else parent,
            clone_chapters,
            clone_exercises,
        )


def set_sis(instance: CourseInstance, id: str) -> None:
    """
    Set teachers, starting time and ending based on Student Information System.

    Parameters
    ----------
    instance
        The course instance to be modified

    id
        Course realisation identifier used by the SIS system
    """
    sis: StudentInfoSystem = get_sis_configuration()
    if not sis:
        # Student Info System not configured
        return
    try:
        coursedata = sis.get_course_data(id)
    except Exception as e:
        logger.exception(f"Error getting course data from SIS.")
        return

    if coursedata.get('starting_time') and coursedata.get('ending_time'):
        instance.starting_time = coursedata['starting_time']
        instance.ending_time = coursedata['ending_time']

    instance.sis_id = id
    instance.save()

    if coursedata['teachers']:
        for i in coursedata['teachers']:
            try:
                user = User.objects.get(username=i)
            except User.DoesNotExist:
                # If user does not exist, create a new user.
                # If external authentication (e.g. Shibboleth) is used, other
                # attributes will be updated when user logs in for the first time.
                user = User.objects.create_user(i)

            instance.add_teacher(user.userprofile)

@transaction.atomic
def clone(
        instance,
        url,
        clone_teachers,
        clone_assistants,
        clone_usertags,
        clone_categories,
        clone_modules,
        clone_chapters,
        clone_exercises,
        clone_menuitems,
        siskey,
):
    """
    Clones the course instance and returns the new saved instance.
    """
    teachers = list(instance.teachers.all())
    assistants = list(instance.assistants.all())
    usertags = list(instance.usertags.all())
    categories = list(instance.categories.all())
    modules = list(instance.course_modules.all())
    menuitems = list(instance.ext_services.all())

    # Save as new course instance.
    instance.id = None
    instance.visible_to_students = False
    instance.url = url
    instance.save()

    if clone_teachers:
        instance.set_teachers(teachers)

    if clone_assistants:
        instance.set_assistants(assistants)

    if siskey and siskey != 'none':
        set_sis(instance, siskey)

    if clone_usertags:
        for usertag in usertags:
            usertag.id = None
            usertag.course_instance = instance
            usertag.save()

    category_map = {}
    if clone_categories:
        for category in categories:
            old_id = category.id

            # Save as new category.
            category.id = None
            category.course_instance = instance
            category.save()

            category_map[old_id] = category

    if clone_modules:
        for module in modules:
            objects = list(module.learning_objects.filter(parent__isnull=True))

            # Save as new module.
            module.id = None
            module.course_instance = instance
            module.save()

            clone_learning_objects(
                category_map,
                module,
                objects,
                None,
                clone_chapters,
                clone_exercises,
            )

    if clone_menuitems:
        for menuitem in menuitems:
            menuitem.id = None
            menuitem.course_instance = instance
            menuitem.save()

    return instance
