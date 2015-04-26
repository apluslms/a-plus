'''
Provides LTI access to external services with current course and user identity.

'''
#from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, render_to_response
from django.http import HttpResponseForbidden, Http404
from django.template.context import RequestContext
from django.utils.translation import get_language
from .models import MenuItem
import requests_oauthlib as oath2
import hashlib, datetime, calendar, uuid


#@login_required
def lti_login(request, menu_id):
    '''
    Generates an LTI POST form for a service.
    Implements LTI 1.0 using required and most recommended parameters.
    Tested for use with Piazza, https://piazza.com/product/lti

    @type request: C{django.http.HttpRequest}
    @param requet: an HTTP request
    @type menu_id: C{str}
    @param menu_id: an LTI menu item id
    @rtype: C{django.http.HttpResponse}
    @return: an HTTP response
    '''
    menu_item = get_object_or_404(MenuItem, pk=menu_id)
    service = menu_item.service.as_leaf_class()

    # Check that service and menu item are enabled.
    if not menu_item.enabled or not service.enabled:
        raise Http404()

    course_instance = menu_item.course_instance
    course = course_instance.course

    # Get user and control access.
    user = request.user
    user_profile = user.userprofile
    if not course_instance.is_visible_to(user_profile):
        return HttpResponseForbidden("You are not allowed to access this view.")

    # Determine user ID.
    student_id = "aplusuid%d" % (user.pk)
    if user_profile.student_id:
        student_id = user_profile.student_id

    # MD5 the user id so that the real student id and names or emails are not linked.
    student_id = hashlib.md5(student_id).hexdigest()

    # Determine user role.
    role = "Student"
    if course_instance.is_teacher(user_profile):
        role = "Instructor"
    elif course_instance.is_assistant(user_profile):
        role = "TA"

    parameters = {

        "lti_version": "LTI-1p0",
        "lti_message_type": "basic-lti-launch-request",

        "resource_link_id": "aplus%d" % (service.pk),
        "resource_link_title": menu_item.label,

        # User session.
        "user_id": student_id,
        "roles": role,
        "lis_person_name_full": "%s %s" % (user.first_name, user.last_name),
        "lis_person_name_given": user.first_name,
        "lis_person_name_family": user.last_name,
        "lis_person_contact_email_primary": user.email,

        # Selected course.
        "context_id": request.get_host() + course_instance.get_absolute_url(),
        "context_title": course.name,
        "context_label": course.code,

        "launch_presentation_locale": get_language(),

        "tool_consumer_instance_guid": request.get_host() + "/aplus",
        "tool_consumer_instance_name": "A+ LMS",

        "oauth_version": "1.0",
        "oauth_timestamp": (calendar.timegm(datetime.datetime.utcnow().utctimetuple())),
        "oauth_nonce": str(uuid.uuid1())
    }

    # Sign the request using OAuth.
    consumer = oauth2.Consumer(key=service.consumer_key, secret=service.consumer_secret)
    oauth_req = oauth2.Request(method="POST", url=service.url, parameters=parameters)
    oauth_req.sign_request(oauth2.SignatureMethod_HMAC_SHA1(), consumer, None)

    return render_to_response("external_services/lti_form.html", RequestContext(request, {
        "url": service.url,
        "parameters": list(oauth_req.items()),
    }))
