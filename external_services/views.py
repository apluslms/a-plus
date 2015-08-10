"""
Provides LTI access to external services with current course and user identity.
"""
import hashlib

from django.core.exceptions import PermissionDenied
from django.http import Http404
from django.shortcuts import get_object_or_404
from django.utils.translation import get_language
from oauthlib.common import urldecode
from oauthlib.oauth1 import Client, SIGNATURE_HMAC, SIGNATURE_TYPE_BODY

from course.viewbase import CourseInstanceBaseView
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
            if not self.is_assistant:
                raise PermissionDenied()

    def get_common_objects(self):
        super().get_common_objects()
        user = self.request.user

        # Determine user ID.
        student_id = "aplusuid%d" % (user.pk)
        if self.profile.student_id:
            student_id = self.profile.student_id

        # MD5 the user id so that the real student id and names or emails
        # are not linked in external services.
        student_id = hashlib.md5(student_id.encode('utf-8')).hexdigest()

        # Determine user role.
        role = "Student"
        if self.is_teacher:
            role = "Instructor"
        elif self.is_assistant:
            role = "TA,TeachingAssistant"

        parameters = {

            "lti_version": "LTI-1p0",
            "lti_message_type": "basic-lti-launch-request",

            "resource_link_id": "aplus%d" % (self.service.pk),
            "resource_link_title": self.menu_item.label,

            # User session.
            "user_id": student_id,
            "roles": role,
            "lis_person_name_full": "%s %s" % (user.first_name, user.last_name),
            "lis_person_name_given": user.first_name,
            "lis_person_name_family": user.last_name,
            "lis_person_contact_email_primary": user.email,

            # Selected course.
            "context_id": self.request.get_host() \
                + self.instance.get_absolute_url(),
            "context_title": self.course.name,
            "context_label": self.course.code,

            "launch_presentation_locale": get_language(),

            "tool_consumer_instance_guid": self.request.get_host() + "/aplus",
            "tool_consumer_instance_name": "A+ LMS",
        }
        headers = {
            "Content-Type": "application/x-www-form-urlencoded",
        }

        # Sign the request using OAuth.
        client = Client(self.service.consumer_key,
            client_secret=self.service.consumer_secret,
            signature_method=SIGNATURE_HMAC,
            signature_type=SIGNATURE_TYPE_BODY)
        uri, headers, body = client.sign(self.service.url,
            http_method="POST",
            body=parameters,
            headers=headers)
        self.url = uri
        self.parameters = urldecode(body)
        self.note("url", "parameters")
