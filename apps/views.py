from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, render_to_response
from django.template.context import RequestContext

from apps.models import BaseTab
from userprofile.models import UserProfile
from course.models import CourseInstance
from django.http.response import HttpResponseForbidden


@login_required
def view_tab(request, tab_id):
    
    tab_object = get_object_or_404(BaseTab, id=tab_id).as_leaf_class()
    
    # Check for access.
    if isinstance(tab_object.container, CourseInstance):
        if not tab_object.container.is_visible_to(request.user):
            return HttpResponseForbidden()
    
    tab_renderer = tab_object.get_renderer_class()(
       tab_object,
       UserProfile.get_by_request(request),
       tab_object.get_container()
    )
    return render_to_response("plugins/view_tab.html", RequestContext(request, {
        "tab": tab_renderer,
        "instance": tab_object.get_container()
    }))
