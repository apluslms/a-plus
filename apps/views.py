# Django
from django.shortcuts import get_object_or_404, render_to_response
from django.template.context import RequestContext
from django.contrib.auth.decorators import login_required

# A+
from apps.models import BaseTab

@login_required
def view_tab(request, tab_id):
    tab_object = get_object_or_404(BaseTab, id=tab_id).as_leaf_class()
    tab_renderer = tab_object.get_renderer_class()(tab_object,
                                                   request.user.userprofile,
                                                   tab_object.get_container())

    return render_to_response("plugins/view_tab.html",
                              RequestContext(request,
                                     {"tab": tab_renderer,
                                      "instance": tab_object.get_container()}))
