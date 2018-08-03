from hashlib import md5
from django.core.exceptions import PermissionDenied
from django.utils.translation import get_language
from rest_framework.reverse import reverse
from rest_framework.settings import api_settings
from oauthlib.common import urldecode
from oauthlib.oauth1 import Client, SIGNATURE_HMAC, SIGNATURE_TYPE_BODY, \
    SIGNATURE_TYPE_QUERY
import json

from aplus.api import api_reverse
from lib.helpers import update_url_params
from course.models import Enrollment


class LTIRequest(object):

    def __init__(self, service, user, instance, request, title, context_id=None, link_id=None, add=None, exercise=None):
        self.service = service
        course = instance.course
        # Context and resource parameters.
        context_id = context_id or (request.get_host() + instance.get_absolute_url())
        link_id = link_id or "aplus{:d}".format(service.pk)
        title = title or link_id

        # Gather user information
        user_id, given_name, family_name, full_name, email = self.user_info(instance, user)

        # Determine user role.
        role = "Learner,Student"
        # Student is not a standard role name, but it has been used here before
        if course.is_teacher(user):
            role = "Instructor"
        elif instance.is_assistant(user):
            role = "TA,TeachingAssistant" # "TA" is not a standard role

        self.parameters = add or {}
        self.parameters.update({

            "lti_version": "LTI-1p0",
            "lti_message_type": "basic-lti-launch-request",

            "resource_link_id": link_id,
            "resource_link_title": title,

            # User.
            "user_id": user_id,
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
            "launch_presentation_document_target":
                "iframe" if exercise and exercise.open_in_iframe else "window",
            "launch_presentation_return_url": request.scheme + '://' + request.get_host() + instance.get_absolute_url(),

            "tool_consumer_instance_guid": request.get_host() + "/aplus",
            "tool_consumer_instance_name": "A+ LMS",
        })

        if service.api_access:
            self.parameters.update({
                'custom_context_api': request.scheme + '://' + request.get_host() + api_reverse("course-detail", kwargs={'course_id': instance.id}),
                'custom_context_api_id': str(instance.id),
                'custom_user_api_token': user.userprofile.api_token,
            })

        if exercise:
            # LTI 1.1 Tool Provider may return grades to A+ (Tool Consumer)
            self.parameters.update({
                # Outcome Service requests from the LTI Tool Provider include the
                # sourcedid from the launch request. It is used to create new submissions
                # for storing the points of the user.
                "lis_result_sourcedid": "{}-{}".format(exercise.pk, user_id),
                # The LTI Tool Provider posts Outcome Service requests to this URL (i.e., points for a submission)
                "lis_outcome_service_url": reverse('lti-outcomes', request=request,
                                                   kwargs={'version': api_settings.DEFAULT_VERSION}),
            })

    def user_info(self, course_instance, user):
        if self.service.is_anonymous:
            # Anonymize user information
            enrollment = Enrollment.objects.filter(course_instance=course_instance, user_profile=user.userprofile).first()
            if not enrollment:
                raise PermissionDenied()
            # Creates anon name and id for pre-pseudonymisation Enrollments
            if not (enrollment.anon_name or enrollment.anon_id):
                # the model's post_save functions take care of the creation
                enrollment.save()
            user_id = "a" + enrollment.anon_id # a for anonymous
            full_name = enrollment.anon_name
            given_name, sep, family_name = full_name.rpartition(" ")
            if not given_name:
                given_name = "Anonymous"
            email = "anonymous-{}@aplus.invalid".format(enrollment.anon_id)
        else:
            user_id = "i" + str(user.pk) # i for internal
            full_name = "{} {}".format(user.first_name, user.last_name)
            given_name = user.first_name
            family_name = user.last_name
            email = user.email
        return user_id, given_name, family_name, full_name, email

    def get_checksum_of_parameters(self, only_user_and_course_level_params=False):
        if only_user_and_course_level_params:
            # do not include parameters that change between different exercises for the same LTI service
            included_keys = (
                "lti_version",
                "lti_message_type",
                "user_id",
                "lis_person_name_full",
                "lis_person_contact_email_primary",
                "context_id",
                "context_label",
                "tool_consumer_instance_guid",
            )
            params = [(key, value) for key, value in self.parameters.items() if key in included_keys]
        else:
            params = self.parameters.items()
        sum = md5()
        for key, value in sorted(params):
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

    def __init__(self, service, user, profiles, instance, request, title, context_id=None, link_id=None, add=None, exercise=None):
        self.service = service
        self.course_instance = instance
        parameters = add or {}
        if not service.is_anonymous:
            parameters['custom_student_id'] = self.true_student_id(user.userprofile)
        if len(profiles) > 1:
            parameters['custom_group_members'] = self.group_json(profiles)
        super().__init__(service, user, instance, request, title, context_id, link_id, parameters, exercise)

    def true_student_id(self, profile):
        return profile.student_id or "A{:d}".format(profile.id)

    def group_json(self, profiles):
        data = []
        for profile in profiles:
            user_id, given_name, family_name, full_name, email = self.user_info(self.course_instance, profile.user)
            d = {
                'user': user_id,
                'given_name': given_name,
                'family_name': family_name,
                'full_name': full_name,
                'email': email,
            }
            if not self.service.is_anonymous:
                d['student_id'] = self.true_student_id(profile)
            data.append(d)
        return json.dumps(data)
