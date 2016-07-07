'''
Utility functions for exercise templates.

'''
from django.template import loader, Context
from django.shortcuts import render
from access.config import ConfigError
from .personalized import personalized_template_context

def render_configured_template(request, course, exercise, post_url, default=None, result=None):
    '''
    Renders a configured or optional default template.

    @type request: C{django.http.request.HttpRequest}
    @param request: a request to handle
    @type course: C{dict}
    @param course: a course configuration
    @type exercise: C{dict}
    @param exercise: an exercise configuration
    @type post_url: C{str}
    @param post_url: the post URL for the exercise
    @type default: C{str}
    @param default: a default template name to use if not configured
    @type result: C{dict}
    @param result: results from grading
    @rtype: C{django.http.response.HttpResponse}
    @return: a response
    '''
    template = None
    if "template" in exercise:
        template = exercise["template"]
    elif default is not None:
        template = default
    else:
        raise ConfigError("Missing \"template\" in exercise configuration.")
    
    return render_template(request, course, exercise, post_url, template, result)


def render_template(request, course, exercise, post_url, template, result=None):
    '''
    Renders a template.

    @type request: C{django.http.request.HttpRequest}
    @param request: a request to handle
    @type course: C{dict}
    @param course: a course configuration
    @type exercise: C{dict}
    @param exercise: an exercise configuration
    @type post_url: C{str}
    @param post_url: the post URL for the exercise
    @type template: C{str}
    @param template: a template name to use
    @type result: C{dict}
    @param result: results from grading: may include error=True, accepted=True, points=%d
    @rtype: C{django.http.response.HttpResponse}
    @return: a response
    '''
    if template.startswith('./'):
        template = course['key'] + template[1:]
    return render(request, template,
        _exercise_context(course, exercise, post_url, result, request))


def template_to_str(course, exercise, post_url, template, result=None):
    '''
    Renders a template to text string.

    @type course: C{dict}
    @param course: a course configuration
    @type exercise: C{dict}
    @param exercise: an exercise configuration
    @type post_url: C{str}
    @param post_url: the post URL for the exercise
    @type template: C{str}
    @param template: a template name to use
    @type result: C{dict}
    @param result: additional results
    @rtype: C{str}
    @return: rendered template content
    '''
    if template.startswith('./'):
        template = course['key'] + template[1:]
    tpl = loader.get_template(template)
    return tpl.render(_exercise_context(course, exercise, post_url, result))


def _exercise_context(course, exercise, post_url, result=None, request=None):
    ctx = {
        "request": request,
        "course": course,
        "exercise": exercise,
        "post_url": post_url or "",
        "result": result,
    }
    if "personalized" in exercise and exercise["personalized"] and request:
        ctx.update(personalized_template_context(course, exercise, request))
    return ctx
