from django.db import transaction

def clone_learning_objects(category_map, module, objects, parent):
    """
    Clones learning objects recursively.
    """
    for lobject in list(a.as_leaf_class() for a in objects):
        children = list(lobject.children.all())

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

        clone_learning_objects(category_map, module, children, lobject)


@transaction.atomic
def clone(instance, url):
    """
    Clones the course instance and returns the new saved instance.
    """
    assistants = list(instance.assistants.all())
    usertags = list(instance.usertags.all())
    categories = list(instance.categories.all())
    modules = list(instance.course_modules.all())

    # Save as new course instance.
    instance.id = None
    instance.visible_to_students = False
    instance.url = url
    instance.save()

    instance.assistants.add(*assistants)

    for usertag in usertags:
        usertag.id = None
        usertag.course_instance = instance
        usertag.save()

    category_map = {}
    for category in categories:
        old_id = category.id

        # Save as new category.
        category.id = None
        category.course_instance = instance
        category.save()

        category_map[old_id] = category

    for module in modules:
        objects = list(module.learning_objects.filter(parent__isnull=True))

        # Save as new module.
        module.id = None
        module.course_instance = instance
        module.save()

        clone_learning_objects(category_map, module, objects, None)

    return instance
