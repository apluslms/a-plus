# Django
from django.http import HttpResponse
from django.shortcuts import render_to_response
from django.template.context import RequestContext
from userprofile.models import StudentGroup

# OAuth
from oauth_provider.forms import AuthorizeRequestTokenForm


def oauth_authorize(request, token, callback, params):
    form = AuthorizeRequestTokenForm(initial={"oauth_token": token.key})
    return render_to_response("oauth/authorize.html", 
                              RequestContext(request, {"token": token, "form": form}))
