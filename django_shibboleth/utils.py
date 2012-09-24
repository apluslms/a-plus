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

from django.conf import settings
from django.shortcuts import render_to_response
from django.template import RequestContext
from django.http import HttpResponseRedirect

def parse_attributes(META):
    shib_attrs = {}
    error = False
    for header, attr in settings.SHIB_ATTRIBUTE_MAP.items():
        required, name = attr
        values = META.get(header, None)
        value = None
        if values:
            # If multiple attributes releases just care about the 1st one
            try:
                value = values.split(';')[0]
            except:
                value = values
                
        shib_attrs[name] = value
        if not value or value == '':
            if required:
                error = True
    return shib_attrs, error


def build_shib_url(request, target, entityid=None):
    url_base = 'https://%s' % request.get_host()
    shib_url = "%s%s" % (url_base, getattr(settings, 'SHIB_HANDLER', '/Shibboleth.sso/DS'))
    if not target.startswith('http'):
        target = url_base + target

    url = '%s?target=%s' % (shib_url, target)
    if entityid:
        url += '&entityID=%s' % entityid
    return url


def ensure_shib_session(request):
    if 'HTTP_SHIB_SESSION_ID' in request.META and request.META['HTTP_SHIB_SESSION_ID']:
        
    
        attr, error = parse_attributes(request.META)
        if error:
            return render_to_response('shibboleth/attribute_error.html', 
                                      {'shib_attrs': attr}, 
                                      context_instance=RequestContext(request))
        return None
    else:
        return HttpResponseRedirect(build_shib_url(request, request.build_absolute_uri()))
    

