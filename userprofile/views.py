from django.conf import settings
from django.contrib.auth import REDIRECT_FIELD_NAME
from django.contrib.auth.decorators import login_required
from django.contrib.auth.views import login as django_login
from django.http.response import HttpResponseRedirect
from django.shortcuts import render_to_response, resolve_url
from django.template.context import RequestContext
from django.utils.http import is_safe_url

from .models import StudentGroup


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
        redirect_to = request.POST.get(REDIRECT_FIELD_NAME,
                                       request.GET.get(REDIRECT_FIELD_NAME, ''))
        if not is_safe_url(url=redirect_to, host=request.get_host()):
            redirect_to = resolve_url(settings.LOGIN_REDIRECT_URL)
        return HttpResponseRedirect(redirect_to)

    return django_login(
        request,
        template_name="userprofile/login.html",
        extra_context={
            'shibboleth_login': 'shibboleth_login' in settings.INSTALLED_APPS,
            'login_title_text': settings.LOGIN_TITLE_TEXT,
            'login_body_text': settings.LOGIN_BODY_TEXT,
            'login_button_text': settings.LOGIN_BUTTON_TEXT,
        }
    )


@login_required
def view_groups(request):
    '''
    Displays the student groups available in the system.
    TODO: The students are not able to create new groups or join or quit groups.

    @param request: the HttpRequest object from Django
    '''

    groups = StudentGroup.objects.all()
    context = RequestContext(request, {"groups": groups})
    return render_to_response("userprofile/view_groups.html", context)
