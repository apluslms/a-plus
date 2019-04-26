from django import template
from django.urls import reverse

from course.models import CourseInstance


register = template.Library()


def _normal_kwargs(instance, model_name, **extra_kwargs):
    kwargs = instance.get_url_kwargs()
    kwargs.update({
        "model": model_name,
    })
    kwargs.update(extra_kwargs)
    return kwargs


@register.filter
def editurl(model_object, model_name):
    return reverse('model-edit', kwargs=_normal_kwargs(
        model_object.course_instance,
        model_name,
        id=model_object.id,
    ))


@register.filter
def removeurl(model_object, model_name):
    return reverse('model-remove', kwargs=_normal_kwargs(
        model_object.course_instance,
        model_name,
        id=model_object.id,
    ))


@register.filter
def createurl(model_object, model_name):
    type_name = None
    if "," in model_name:
        model_name, type_name = model_name.split(",", 1)
    if isinstance(model_object, CourseInstance):
        return reverse('model-create', kwargs=_normal_kwargs(
            model_object,
            model_name,
        ))
    if type_name:
        return reverse('model-create-type-for', kwargs=_normal_kwargs(
            model_object.course_instance,
            model_name,
            parent_id=model_object.id,
            type=type_name,
        ))
    return reverse('model-create-for', kwargs=_normal_kwargs(
        model_object.course_instance,
        model_name,
        parent_id=model_object.id,
    ))
