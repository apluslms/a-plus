from django import template
from django.core.urlresolvers import reverse

from exercise.templatetags.exercise import _prepare_context
from ..grade import assign_grade
from ..models import CourseDiplomaDesign


register = template.Library()


@register.inclusion_tag("diploma/_diploma_button.html", takes_context=True)
def diploma_button(context, student=None):
    points = _prepare_context(context, student)
    design = CourseDiplomaDesign.objects.filter(course=points.instance).first()
    url = None
    if design and points.user.is_authenticated():
        url = reverse('diploma-create', kwargs={
            'coursediploma_id': design.id,
            'userprofile_id': points.user.userprofile.id,
        })
    return {
        'grade': assign_grade(points, design),
        'url': url,
        'is_course_staff': context.get('is_course_staff'),
    }
