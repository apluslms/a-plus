from django import template

from course.models import CourseInstance


register = template.Library()


@register.inclusion_tag("course/_course_dropdown_menu.html", takes_context=True)
def course_menu(context):
    return { "instances": CourseInstance.objects.get_active(context["user"]) }


@register.filter
def url(model_object, name=None):
    if name:
        return model_object.get_url(name)
    return model_object.get_absolute_url()
