from django.shortcuts import render_to_response
from django.template import RequestContext
from django.http import HttpResponseRedirect

from django_shibboleth.utils import parse_attributes, build_shib_url

def shib_required(f):
    def wrap(request, *args, **kwargs):
        if 'HTTP_SHIB_SESSION_ID' in request.META and request.META['HTTP_SHIB_SESSION_ID']:
            attr, error = parse_attributes(request.META)
            if error:
                return render_to_response('shibboleth/attribute_error.html', 
                                          {'shib_attrs': attr}, 
                                          context_instance=RequestContext(request))
        else:
            return HttpResponseRedirect(build_shib_url(request, request.build_absolute_uri()))
        
        return f(request, *args, **kwargs)

    wrap.__doc__=f.__doc__
    wrap.__name__=f.__name__
    return wrap
