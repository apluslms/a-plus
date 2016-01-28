"""
Provides LTI access to external services with current course and user identity.
"""
from django.core.exceptions import PermissionDenied
from django.http import Http404
from django.shortcuts import get_object_or_404

from course.viewbase import CourseInstanceBaseView
from .lti import LTIRequest
from .models import MenuItem


class LTILoginView(CourseInstanceBaseView):
    """
    Generates an LTI POST form for a service.
    Implements LTI 1.0 using required and most recommended parameters.
    Tested for use with Piazza, https://piazza.com/product/lti
    """
    template_name = "external_services/lti_form.html"
    id_kw = "menu_id"

    def get_resource_objects(self):
        super().get_resource_objects()
        self.menu_item = get_object_or_404(
            MenuItem,
            pk=self._get_kwarg(self.id_kw),
            course_instance=self.instance
        )
        self.service = self.menu_item.service.as_leaf_class()

        # Check that service and menu item are enabled.
        if not self.menu_item.enabled or not self.service.enabled:
            raise Http404()

    def access_control(self):
        super().access_control()
        if self.menu_item.access >= MenuItem.ACCESS_TEACHER:
            if not self.is_teacher:
                raise PermissionDenied()
        elif self.menu_item.access >= MenuItem.ACCESS_ASSISTANT:
            if not self.is_course_staff:
                raise PermissionDenied()

    def get_common_objects(self):
        super().get_common_objects()
        lti = LTIRequest(
            self.service,
            self.request.user,
            self.instance,
            self.request.get_host(),
            self.menu_item.label,
        )
        self.url = self.service.url
        self.parameters = lti.sign_post_parameters()
        self.note("url", "parameters")
