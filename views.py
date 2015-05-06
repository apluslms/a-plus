import urllib.parse
import json

from django.shortcuts import render_to_response, redirect
from django.template.context import RequestContext
from django.http import HttpResponse
from django.contrib.auth.decorators import login_required
from django.contrib.auth.views import login as django_login
from django.conf import settings
from django.contrib.auth import REDIRECT_FIELD_NAME

from course.models import Course, CourseInstance,\
    get_visible_open_course_instances
#from oauth_provider.decorators import oauth_required #todo what do?
from django.utils.datetime_safe import datetime

def login(request):
    """
    This login view is a wrapper for the default login view in Django. This view checks if the user
    is already authenticated and if so, it redirects the user straight to the page he/she was 
    trying to access. If no page is accessed, the user is redirected to default address.
    
    If the user has not yet been authenticated, this view will call the default view in Django.
    """
    if request.user.is_authenticated():
        # User is authenticated so we'll just redirect. The following checks for the redirect url 
        # are borrowed from django.contrib.auth.views.login.
        redirect_to = request.REQUEST.get(REDIRECT_FIELD_NAME, '')
        netloc = urllib.parse.urlparse(redirect_to)[1]
        
        # Use default setting if redirect_to is empty
        if not redirect_to:
            redirect_to = settings.LOGIN_REDIRECT_URL
        
        # Security check -- don't allow redirection to a different host.
        elif netloc and netloc != request.get_host():
            redirect_to = settings.LOGIN_REDIRECT_URL
        
        return redirect(redirect_to)
    
    return django_login(request, template_name="aaltoplus/login.html")

def home(request):
    open_instances = CourseInstance.objects.filter(ending_time__gte=datetime.now())

    if request.user.is_authenticated():
        instances = get_visible_open_course_instances(
            request.user.userprofile)
    else:
        instances = get_visible_open_course_instances()

    context = RequestContext(request, {"instances": instances})
    return render_to_response("aaltoplus/home.html", context)

def privacy(request):
    context = RequestContext(request)
    return render_to_response("aaltoplus/privacy.html", context)

#@oauth_required #what do?
def verify_credentials(request):
    json_str = json.dumps({"screen_name": request.user.username})
    return HttpResponse(json_str, content_type="text/plain")

