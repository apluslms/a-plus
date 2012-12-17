import urlparse

from django.shortcuts import render_to_response, redirect
from django.template.context import RequestContext
from django.http import HttpResponse
from django.utils import simplejson
from django.contrib.auth.decorators import login_required
from django.contrib.auth.views import login as django_login
from django.conf import settings
from django.contrib.auth import REDIRECT_FIELD_NAME

from course.models import Course, CourseInstance
from oauth_provider.decorators import oauth_required
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
        netloc = urlparse.urlparse(redirect_to)[1]
        
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

    if request.user.is_authenticated and (request.user.is_staff
                                          or request.user.is_superuser):
        visible_open_instances = list(open_instances)
    else:
        visible_open_instances = []
        for i in open_instances:
            if i.visible_to_students or (request.user.is_authenticated() and
                                        i.is_staff(request.user.get_profile())):
                visible_open_instances.append(i)

    context = RequestContext(request, {"open_instances": visible_open_instances})
    return render_to_response("aaltoplus/home.html", context)

def privacy(request):
    context = RequestContext(request)
    return render_to_response("aaltoplus/privacy.html", context)

@oauth_required
def verify_credentials(request):
    json_str = simplejson.dumps({"screen_name": request.user.username})
    return HttpResponse(json_str, content_type="text/plain")

