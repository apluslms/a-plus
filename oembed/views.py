import json
from urllib.parse import urlparse, urlunparse
from django.core.urlresolvers import resolve
from django.http import HttpResponse, HttpResponseBadRequest
from django.template.loader import render_to_string
from exercise.views import view_exercise as original_view_exercise


def get_oembed(request):
    # according to spec, only GET should be supported..
    if request.method != "GET":
        return HttpResponse("%s not allowed" % request.method, status=405)
    # .. and url is a required parameter
    if "url" not in request.GET:
        return HttpResponseBadRequest()
    # check if the user is authenticated, if not respond with status 403
    if not request.user.is_authenticated():
        return HttpResponse('Unauthorized', status=401)

    # parse the given url..
    resource_url = urlparse(request.GET['url'])
    # .. and make it "relative" by stripping scheme and domain parts ..
    relative_url = urlunparse(('', '', resource_url.path, resource_url.params,
                              resource_url.query, resource_url.fragment))
    # .. to be able to do a resolve to django URLs to get the exercise_id
    exercise_id = resolve(relative_url).kwargs['exercise_id']

    # render the original exercise view with oembed template, returns 404 if no such exercise
    html = original_view_exercise(request, exercise_id, template="oembed/view_exercise.html").content

    # prepare the data to be rendered
    response_data = {
        "version": "1.0",
        "type": "rich",
        "html": html,
        "width": "800",   # oembed requires width and height, A+ has no way of knowing them
        "height": "600",  # we'll use sensible defaults here
    }

    # default to JSON format
    format = request.GET.get('format', 'json')
    if format == 'json':
        return _jsonresponse(request, response_data)
    elif format == 'xml':
        return _xmlresponse(request, response_data)
    else:
        # if not a known format, return HTTP Error 501 Not implemented (as per specs)
        return HttpResponse("Unknown format: %s" % format, status=501)


def _jsonresponse(request, data):
    respjson = json.dumps(data)
    if 'callback' in request.GET:
        respjson = '%s(%s);' % (request.GET['callback'], respjson)
    return HttpResponse(respjson, content_type="application/json")


def _xmlresponse(request, data):
    return HttpResponse(render_to_string("oembed/xmlresponse.xml", {"data": data}), content_type="text/xml")
