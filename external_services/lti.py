from hashlib import md5
from django.core.exceptions import PermissionDenied
from django.utils.translation import get_language
from oauthlib.common import urldecode
from oauthlib.oauth1 import Client, SIGNATURE_HMAC, SIGNATURE_TYPE_BODY, \
    SIGNATURE_TYPE_QUERY
import hashlib
import json

from aplus.api import api_reverse
from lib.helpers import update_url_params
from course.models import Enrollment


class LTIRequest(object):

    def __init__(self, service, user, instance, host, title, context_id=None, link_id=None, add=None):
        self.service = service
        course = instance.course
        # Context and resource parameters.
        context_id = context_id or (host + instance.get_absolute_url())
        link_id = link_id or "aplus{:d}".format(service.pk)
        title = title or link_id

        # Gather user information
        if service.is_anonymous:
            # Anonymize user information
            enrollment = Enrollment.objects.filter(course_instance=instance, user_profile=user.userprofile).first()
            if not enrollment:
                raise PermissionDenied()
            # Creates anon name and id for pre-pseudonymisation Enrollments
            if not (enrollment.anon_name or enrollment.anon_id):
                # the model's post_save functions take care of the creation
                enrollment.save()
            student_id = "a" + enrollment.anon_id # a for anonymous
            full_name = enrollment.anon_name
            given_name, sep, family_name = full_name.rpartition(" ")
            if not given_name:
                given_name = "Anonymous"
            email = "anonymous-{}@aplus.invalid".format(enrollment.anon_id)
        else:
            student_id = "i" + self.external_student_id(user) # i for internal
            full_name = "{} {}".format(user.first_name, user.last_name)
            given_name = user.first_name
            family_name = user.last_name
            email = user.email

        # Determine user role.
        role = "Student"
        if course.is_teacher(user):
            role = "Instructor"
        elif instance.is_assistant(user):
            role = "TA,TeachingAssistant"

        self.parameters = add or {}
        self.parameters.update({

            "lti_version": "LTI-1p0",
            "lti_message_type": "basic-lti-launch-request",

            "resource_link_id": link_id,
            "resource_link_title": title,

            # User.
            "user_id": student_id,
            "roles": role,
            "lis_person_name_full": full_name,
            "lis_person_name_given": given_name,
            "lis_person_name_family": family_name,
            "lis_person_contact_email_primary": email,

            # Selected course.
            "context_id": context_id,
            "context_title": course.name,
            "context_label": course.code,

            "launch_presentation_locale": get_language(),

            "tool_consumer_instance_guid": host + "/aplus",
            "tool_consumer_instance_name": "A+ LMS",
        })

        if service.api_access:
            self.parameters.update({
                # FIXME: we need request or full host with protocol here!
                'custom_context_api': '//' + host + api_reverse("course-detail", kwargs={'course_id': instance.id}),
                'custom_context_api_id': str(instance.id),
                'custom_user_api_token': user.userprofile.api_token,
            })

    def external_student_id(self, user):
        student_id = user.userprofile.student_id \
            if user.userprofile.student_id \
            else "aplusuid{:d}".format(user.pk)

        # MD5 the id so that the real student id and names or emails
        # are not linked in external services.
        return hashlib.md5(student_id.encode('utf-8')).hexdigest()

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


class CustomStudentInfoLTIRequest(LTIRequest):

    def __init__(self, service, user, profiles, instance, host, title, context_id=None, link_id=None, add=None):
        parameters = add or {}
        parameters['custom_student_id'] = self.true_student_id(user.userprofile)
        if len(profiles) > 1:
            parameters['custom_group_members'] = self.group_json(profiles)
        super().__init__(service, user, instance, host, title, context_id, link_id, parameters)

    def true_student_id(self, profile):
        return profile.student_id or "A{:d}".format(profile.id)

    def group_json(self, profiles):
        data = [];
        for profile in profiles:
            user = profile.user
            data.append({
                'user': self.external_student_id(user),
                'student_id': self.true_student_id(profile),
                'given_name': user.first_name,
                'family_name': user.last_name,
                'full_name': "{} {}".format(user.first_name, user.last_name),
                'email': user.email,
            })
        return json.dumps(data)
