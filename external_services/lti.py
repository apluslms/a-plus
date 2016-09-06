from hashlib import md5
from django.utils.translation import get_language
from oauthlib.common import urldecode
from oauthlib.oauth1 import Client, SIGNATURE_HMAC, SIGNATURE_TYPE_BODY, \
    SIGNATURE_TYPE_QUERY
import hashlib

from aplus.api import api_reverse
from lib.helpers import update_url_params


class LTIRequest(object):

    def __init__(self, service, user, instance, host, title, context_id=None, link_id=None, add={}):
        self.service = service
        course = instance.course

        # Context and resource parameters.
        context_id = context_id or (host + instance.get_absolute_url())
        link_id = link_id or "aplus{:d}".format(service.pk)
        title = title or link_id

        # Determine user ID.
        student_id = user.userprofile.student_id \
            if user.userprofile.student_id \
            else "aplusuid{:d}".format(user.pk)

        # MD5 the user id so that the real student id and names or emails
        # are not linked in external services.
        student_id = hashlib.md5(student_id.encode('utf-8')).hexdigest()

        # Determine user role.
        role = "Student"
        if course.is_teacher(user):
            role = "Instructor"
        elif instance.is_assistant(user):
            role = "TA,TeachingAssistant"

        self.parameters = add.copy()
        self.parameters.update({

            "lti_version": "LTI-1p0",
            "lti_message_type": "basic-lti-launch-request",

            "resource_link_id": link_id,
            "resource_link_title": title,

            # User.
            "user_id": student_id,
            "roles": role,
            "lis_person_name_full": "{} {}".format(user.first_name, user.last_name),
            "lis_person_name_given": user.first_name,
            "lis_person_name_family": user.last_name,
            "lis_person_contact_email_primary": user.email,

            # Selected course.
            "context_id": context_id,
            "context_title": course.name,
            "context_label": course.code,

            "launch_presentation_locale": get_language(),

            "tool_consumer_instance_guid": host + "/aplus",
            "tool_consumer_instance_name": "A+ LMS",
        })

        if service.enable_api_access:
            self.parameters.update({
                # FIXME: we need request or full host with protocol here!
                'custom_context_api': '//' + host + api_reverse("course-detail", kwargs={'course_id': instance.id}),
                'custom_context_api_id': str(instance.id),
                'custom_user_api_token': user.userprofile.api_token,
            })

    def get_checksum_of_parameters(self):
        sum = md5()
        for key, value in sorted(self.parameters.items()):
            sum.update("{}={};".format(key, value).encode('utf-8'))
        return sum.hexdigest()

    def sign_post_parameters(self, url=None):
        client = Client(self.service.consumer_key,
            client_secret=self.service.consumer_secret,
            signature_method=SIGNATURE_HMAC,
            signature_type=SIGNATURE_TYPE_BODY)
        uri, headers, body = client.sign(url or self.service.url,
            http_method="POST",
            body=self.parameters,
            headers={"Content-Type": "application/x-www-form-urlencoded"})
        return urldecode(body)

    def sign_get_query(self, url=None):
        client = Client(self.service.consumer_key,
            client_secret=self.service.consumer_secret,
            signature_method=SIGNATURE_HMAC,
            signature_type=SIGNATURE_TYPE_QUERY)
        uri = update_url_params(url or self.service.service.url, self.parameters)
        query, headers, body = client.sign(uri, http_method="GET")
        return query
