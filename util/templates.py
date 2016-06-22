'''
Utility functions for exercise templates.

'''
import os
from django.core.urlresolvers import reverse
from django.template import loader, Context
from django.shortcuts import render
from access.config import ConfigError
from access.types.auth import get_uid
from .personalized import prepare_user_personal_directory, read_user_personal_file, \
    select_generated_exercise_instance

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
    if "personalized" in exercise and exercise["personalized"]:
        user_ids = get_uid(request)
        if not user_ids:
            raise ConfigError('Exercise is personalized but HTTP GET request did not supply any "uid" parameter.')
        prepare_user_personal_directory(course, exercise, user_ids)
        
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
    return tpl.render(Context(
        _exercise_context(course, exercise, post_url, result)))


def _exercise_context(course, exercise, post_url, result=None, request=None):
    ctx = {
        "request": request,
        "course": course,
        "exercise": exercise,
        "post_url": post_url or "",
        "result": result,
    }
    if "personalized" in exercise and exercise["personalized"] and request:
        if "generated_files" not in exercise:
            raise ConfigError('"generated_files" missing in the configuration of a personalized exercise')
        generated_files = {}
        for gen_file_conf in exercise["generated_files"]:
            if "file" not in gen_file_conf:
                raise ConfigError('"file" under "generated_files" missing in the exercise configuration')
            file_ctx = {}
            file_ctx["file"] = gen_file_conf["file"]
            userid = get_uid(request)
            submission_number = int(request.GET.get("ordinal_number", 1))
            if "url_in_template" in gen_file_conf and gen_file_conf["url_in_template"]:
                exercise_instance = os.path.basename(select_generated_exercise_instance(
                        course, exercise, userid, submission_number))
                # URL to download the exercise generated file
                file_ctx["url"] = reverse('generated-file',
                        args=(course["key"], exercise["key"], exercise_instance, gen_file_conf["file"]))
            if "content_in_template" in gen_file_conf and gen_file_conf["content_in_template"]:
                # read contents of the exercise generated file to a variable
                file_ctx["content"] = read_user_personal_file(course, exercise,
                        userid, gen_file_conf["file"], True, submission_number)
            generated_files[gen_file_conf["key"]] = file_ctx
        ctx["generated_files"] = generated_files
    return ctx
