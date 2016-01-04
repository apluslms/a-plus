'''
Views configurable for exercise AJAX communication.

Functions take arguments:

    @type request: C{django.http.request.HttpRequest}
    @param request: a request to handle
    @type course: C{dict}
    @param course: a course configuration
    @type exercise: C{dict}
    @param exercise: an exercise configuration
    @rtype: C{django.http.response.HttpResponse}
    @return: a response

'''
from django.conf import settings
from django.http.response import HttpResponse, HttpResponseForbidden, JsonResponse

from util.http import post_result
from .auth import make_hash


def storeSubmission(request, course, exercise):
    if request.method != 'POST':
        return HttpResponse('Method not allowed', status=405)

    checksum = request.POST.get('checksum')
    url = request.POST.get('submission_url')
    answer = request.POST.get('answer')
    points = request.POST.get('points')
    max_points = request.POST.get('max_points')
    parts = [url, answer, points, max_points]

    if not url or not answer or not points or not max_points:
        return HttpResponse('Missing parameters', status=422)

    ajax_key = exercise.get('ajax_key') or settings.AJAX_KEY
    if checksum != make_hash(ajax_key, ':'.join(parts)):
        return HttpResponseForbidden()

    template = exercise.get('feedback_template') or 'access/ajax.html'
    post_result(url, course, exercise, template, {
        'points': points,
        'max_points': max_points,
        'grading_data': answer,
    })
    return JsonResponse({'success': True})
