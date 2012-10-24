import urlparse

from django.shortcuts import render_to_response, redirect
from django.template.context import Context, RequestContext
from django.http import HttpResponse, HttpResponseRedirect
from django.utils import simplejson
from django.contrib.auth.decorators import login_required
from django.contrib.auth.views import login as django_login, logout as django_logout_view
from django.conf import settings
from django.contrib.auth import REDIRECT_FIELD_NAME, logout as django_logout

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

@login_required
def logout(request, template_name=None):
    sso_logout_url = request.user.get_profile().sso_logout_url
    return django_logout_view(request, extra_context={"sso_logout_url": sso_logout_url},
        template_name=template_name)
    """
        # TODO: This is ugly because this doesn't consider that there might be other single sign-on services
        # TODO: Also, this might not be the right way to do shibboleth logout.
        # Finds and deletes a cookie set by mod_shibboleth. Not deleting this cookie results in not asking for user's
        # shibboleth credentials when he logs in again after a logout.
        for key, value in request.COOKIES:
            if key.startswith("_shibsession"):
                shib_cookie_key = key
        if shib_cookie_key:
            # TODO: Remove deployment spcific information
            response.delete_cookie(shib_cookie_key, path="/", domain="plus.cs.hut.fi")
    """

def home(request):
    open_instances = CourseInstance.objects.filter(ending_time__gte=datetime.now())
    context = RequestContext(request, {"open_instances": open_instances})
    return render_to_response("aaltoplus/home.html", context)

def privacy(request):
    context = RequestContext(request)
    return render_to_response("aaltoplus/privacy.html", context)

@oauth_required
def verify_credentials(request):
    json_str = simplejson.dumps({"screen_name": request.user.username})
    return HttpResponse(json_str, content_type="text/plain")

