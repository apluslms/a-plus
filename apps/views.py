from django.contrib.auth.decorators import login_required
from django.http.response import HttpResponseForbidden
from django.shortcuts import get_object_or_404, render_to_response

from apps.models import BaseTab
from course.context import CourseContext
from course.models import CourseInstance
from userprofile.models import UserProfile


@login_required
def view_tab(request, tab_id):
    
    tab_object = get_object_or_404(BaseTab, id=tab_id).as_leaf_class()
    container = tab_object.container
    
    # Check for access.
    if isinstance(container, CourseInstance):
        if not container.is_visible_to(request.user):
            return HttpResponseForbidden()

    tab_renderer = tab_object.get_renderer_class()(
       tab_object,
       UserProfile.get_by_request(request),
       container
    )
    if isinstance(container, CourseInstance):
        context = {
            "tab": tab_renderer,
            "course_instance": container
        }
    else:
        context = {
            "tab": tab_renderer,
            "instance": container,
        }
    return render_to_response("plugins/view_tab.html",
                              CourseContext(request, **context))
