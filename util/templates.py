'''
Utility functions for exercise templates.

'''
from django.template import loader, Context
from django.http.response import HttpResponse
from access.config import ConfigError


def render_configured_template(request, course, exercise, default=None, result=None):
    '''
    Renders a configured or optional default template.
    
    @type request: C{django.http.request.HttpRequest}
    @param request: a request to handle
    @type course: C{dict}
    @param course: a course configuration
    @type exercise: C{dict}
    @param exercise: an exercise configuration
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
    return render_template(request, course, exercise, template, result)


def render_template(request, course, exercise, template, result=None):
    '''
    Renders a template.
    
    @type request: C{django.http.request.HttpRequest}
    @param request: a request to handle
    @type course: C{dict}
    @param course: a course configuration
    @type exercise: C{dict}
    @param exercise: an exercise configuration
    @type template: C{str}
    @param template: a template name to use
    @type result: C{dict}
    @param result: results from grading: may include error=True, accepted=True, points=%d
    @rtype: C{django.http.response.HttpResponse}
    @return: a response
    '''
    return HttpResponse(template_to_str(course, exercise, template, result))


def template_to_str(course, exercise, template, result=None):
    '''
    Renders a template to text string.
    
    @type course: C{dict}
    @param course: a course configuration
    @type exercise: C{dict}
    @param exercise: an exercise configuration
    @type template: C{str}
    @param template: a template name to use
    @type result: C{dict}
    @param result: additional results
    @rtype: C{str}
    @return: rendered template content
    '''
    if course is not None and "lang" in course:
        tpl = loader.select_template([ "%s.%s" % (template, course["lang"]), template ])
    else:
        tpl = loader.get_template(template)
    return tpl.render(Context({ "course": course, "exercise": exercise, "result": result }))
