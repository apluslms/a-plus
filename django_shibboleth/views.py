# Copyright 2010 VPAC
#
# This file is part of django_shibboleth.
#
# django_shibboleth is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# django_shibboleth is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with django_shibboleth  If not, see <http://www.gnu.org/licenses/>.

from django.http import HttpResponseRedirect
from django.template import RequestContext
from django.shortcuts import render_to_response
from django.contrib.auth import login
from django.contrib.auth.models import User
from django.conf import settings

from utils import parse_attributes
from forms import BaseRegisterForm
from signals import shib_logon_done


def shib_register(request, RegisterForm=BaseRegisterForm, register_template_name='shibboleth/register.html'):

    attr, error = parse_attributes(request.META)

    was_redirected = False
    if request.REQUEST.has_key('next'):
        was_redirected = True
    redirect_url = request.REQUEST.get('next', settings.LOGIN_REDIRECT_URL)
    context = {'shib_attrs': attr, 
               'was_redirected': was_redirected}
    if error:
        return render_to_response('shibboleth/attribute_error.html', context, context_instance=RequestContext(request))
    try:
        username = attr[settings.SHIB_USERNAME]
    except:
        return render_to_response('shibboleth/attribute_error.html', context, context_instance=RequestContext(request))

    if not attr[settings.SHIB_USERNAME] or attr[settings.SHIB_USERNAME] == '':
        return render_to_response('shibboleth/attribute_error.html', context, context_instance=RequestContext(request))

    if request.method == 'POST':
        form = RegisterForm(request.POST)
        if form.is_valid():
            user = form.save(attr)
    try:
        user = User.objects.get(username=attr[settings.SHIB_USERNAME])
    except User.DoesNotExist:
        form = RegisterForm()
        context = {'form': form, 'next': redirect_url, 'shib_attrs': attr, 'was_redirected': was_redirected, }
        return render_to_response(register_template_name, context, context_instance=RequestContext(request))

    user.set_unusable_password()
    try:
        user.first_name = attr[settings.SHIB_FIRST_NAME]
        user.last_name = attr[settings.SHIB_LAST_NAME]
        # In some cases, user might have Shibboleth names set but no email
        user.email = attr.get(settings.SHIB_EMAIL, 'no-email@noemail.local')
    except:
        pass
    user.save()

    profile = user.get_profile()
    if attr["student_id"] and attr["student_id"] != "":
        # This is because a student might previously have had a student id. In that case, we don't want to erase it.
        profile.student_id = attr["student_id"].split(':')[-1]
    profile.save()

    user.backend = 'django.contrib.auth.backends.ModelBackend'
    login(request, user)
    shib_logon_done.send(sender=shib_register, user=user, shib_attrs=attr)

    if not redirect_url or '//' in redirect_url or ' ' in redirect_url:
        redirect_url = settings.LOGIN_REDIRECT_URL

    return HttpResponseRedirect(redirect_url)


def shib_meta(request):
    
    meta_data = request.META.items()

    return render_to_response('shibboleth/meta.html', {'meta_data': meta_data}, context_instance=RequestContext(request))
