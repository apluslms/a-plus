from exercise.exercise_models import BaseExercise, CourseChapter
from django.db import transaction

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
