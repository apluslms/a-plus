'''
Views configurable for usual asynchronous exercises that receive data
and queue the grading task. The `grader.tasks` module will grade the
task in time following the exercise configuration and respond with a
separate HTTP post to the received submission URL. Typically the
submitted data is stored in a submission directory.

Functions take arguments:

    @type request: C{django.http.request.HttpRequest}
    @param request: a request to handle
    @type course: C{dict}
    @param course: a course configuration
    @type exercise: C{dict}
    @param exercise: an exercise configuration
    @type post_url: C{str}
    @param post_url: the exercise post URL
    @rtype: C{django.http.response.HttpResponse}
    @return: a response

'''
import logging
import copy
import os
from django.conf import settings
from django.core.urlresolvers import reverse
from django.core.exceptions import PermissionDenied
from django.utils import translation

from util.files import create_submission_dir, save_submitted_file, \
    clean_submission_dir, write_submission_file, write_submission_meta
from util.http import not_modified_since, not_modified_response, cache_headers
from util.queue import queue_length
from util.shell import invoke
from util.templates import render_configured_template, render_template, \
    template_to_str
from .auth import make_hash, get_uid
from ..config import ConfigError, DIR
from .. import tasks


LOGGER = logging.getLogger('main')


def acceptPost(request, course, exercise, post_url):
    '''
    Presents a template and accepts post value for grading queue.
    '''
    _requireActions(exercise)
    if not_modified_since(request, exercise):
        return not_modified_response(request, exercise)

    fields = copy.deepcopy(exercise.get("fields", []))
    if request.method == "POST":

        # Parse submitted values.
        miss = False
        for entry in fields:
            entry["value"] = request.POST.get(entry["name"], "").strip()
            if "required" in entry and entry["required"] and not entry["value"]:
                entry["missing"] = True
                miss = True
        if miss:
            result = { "fields": fields, "rejected": True }
        else:

            # Store submitted values.
            sdir = create_submission_dir(course, exercise)
            for entry in fields:
                write_submission_file(sdir, entry["name"], entry["value"])
            return _acceptSubmission(request, course, exercise, post_url, sdir)
    else:
        result = { "fields": fields }

    return cache_headers(
        render_configured_template(
            request, course, exercise, post_url,
            'access/accept_post_default.html', result
        ),
        request,
        exercise
    )


def acceptFiles(request, course, exercise, post_url):
    '''
    Presents a template and accepts files for grading queue.
    '''
    _requireActions(exercise)
    if not_modified_since(request, exercise):
        return not_modified_response(request, exercise)

    result = None

    # Receive post.
    if request.method == "POST" and "files" in exercise:

        # Confirm that all required files were submitted.
        files_submitted = [] # exercise["files"] entries for the files that were really submitted
        for entry in exercise["files"]:
            # by default, all fields are required
            required = ("required" not in entry or entry["required"])
            if entry["field"] not in request.FILES:
                if required:
                    result = { "rejected": True, "missing_files": True }
                    break
            else:
                files_submitted.append(entry)

        if result is None:
            if "required_number_of_files" in exercise and \
                    exercise["required_number_of_files"] > len(files_submitted):
                result = { "rejected": True, "missing_files": True }
            else:
                # Store submitted files.
                sdir = create_submission_dir(course, exercise)
                for entry in files_submitted:
                    save_submitted_file(sdir, entry["name"], request.FILES[entry["field"]])
                return _acceptSubmission(request, course, exercise, post_url, sdir)

    return cache_headers(
        render_configured_template(
            request, course, exercise, post_url,
            "access/accept_files_default.html", result
        ),
        request,
        exercise
    )


def acceptAttachedExercise(request, course, exercise, post_url):
    '''
    Accepts attached exercise rules and user files for queue.
    '''
    _requireActions(exercise)
    if not_modified_since(request, exercise):
        return not_modified_response(request, exercise)

    result = None

    # Receive post.
    if request.method == "POST":

        # Search for file contents.
        if "file[]" in request.FILES:
            file_list = request.FILES.getlist("file[]")
        else:
            file_list = []
            i = 0
            while "content_%d" % (i) in request.FILES:
                file_list.append(request.FILES["content_%d" % (i)])
                i += 1

        # Store submitted files.
        if not file_list:
            result = { "rejected":True, "missing_files":True }
        else:
            sdir = create_submission_dir(course, exercise)
            i = 0
            for content in file_list:
                if i > 0:
                    key = "file_%d" % (i)
                    if not key in request.POST or not request.POST[key]:
                        result = { "error": True, "missing_file_name": True }
                        clean_submission_dir(sdir)
                        break
                    save_submitted_file(sdir, request.POST[key], content)
                else:
                    save_submitted_file(sdir, "exercise_attachment", content)
                i += 1
            if result is None:
                return _acceptSubmission(request, course, exercise, post_url, sdir)

    # Add the attachment as a hint to the default view form.
    if result is None:
        import copy
        exercise = copy.deepcopy(exercise)
        exercise["files"] = [ { "field": "content_0", "name": "exercise_attachment" } ]

    return cache_headers(
        render_configured_template(
            request, course, exercise, post_url,
            "access/accept_files_default.html", result
        ),
        request,
        exercise
    )


def acceptGitAddress(request, course, exercise, post_url):
    '''
    Presents a template and accepts Git URL for grading.
    '''
    _requireActions(exercise)
    if not_modified_since(request, exercise):
        return not_modified_response(request, exercise)

    result = None

    # Receive post.
    if request.method == "POST" and "git" in request.POST and request.POST["git"].strip():
        source = request.POST["git"]

        # Safe gitlab addresses.
        if "require_gitlab" in exercise:
            if not source.startswith("git@%s:" % (exercise["require_gitlab"])):
                url_start = "https://%s/" % (exercise["require_gitlab"])
                if source.startswith(url_start):
                    url_start_len = len(url_start)
                    url_parts = source[url_start_len:].split("/")
                    if len(url_parts) > 1:
                        source = "git@%s:%s/%s" % (exercise["require_gitlab"], url_parts[0], url_parts[1])
                        if not source.endswith(".git"):
                            source += ".git"
                    else:
                        result = { "error": True, "invalid_address": True }
                else:
                    result = { "error": True, "invalid_address": True }

        # Try to prevent shell injections.
        elif "\"" in source or ";" in source:
            result = { "error": True, "invalid_address": True }

        if result is None:
            sdir = create_submission_dir(course, exercise)
            write_submission_file(sdir, "gitsource", source)
            return _acceptSubmission(request, course, exercise, post_url, sdir)

    return cache_headers(
        render_configured_template(
            request, course, exercise, post_url,
            "access/accept_git_default.html", result
        ),
        request,
        exercise
    )


def acceptGitUser(request, course, exercise, post_url):
    '''
    Presents a template and expects a user id to create Git URL for grading.
    '''
    auth_secret = "*AYVhD'b5,hKzf/6"

    _requireActions(exercise)
    if not "git_address" in exercise:
        raise  ConfigError("Missing \"git_address\" in exercise configuration.")

    user = get_uid(request)
    if request.method == "POST":
        if "user" in request.POST and "hash" in request.POST:
            user = request.POST["user"]
            if make_hash(auth_secret, user) != request.POST["hash"]:
                raise PermissionDenied()
        source = exercise["git_address"].replace("$USER", user)
        sdir = create_submission_dir(course, exercise)
        write_submission_file(sdir, "gitsource", source)
        return _acceptSubmission(request, course, exercise, post_url, sdir)

    return render_configured_template(request, course, exercise, post_url,
        "access/accept_git_user.html", {
            "user": user,
            "hash": make_hash(auth_secret, user)
        })


def _requireActions(exercise):
    '''
    Checks that some actions are set.
    '''
    if "actions" not in exercise or len(exercise["actions"]) == 0:
        if not settings.CONTAINER_MODE or "container" not in exercise:
            raise ConfigError("Missing \"actions\" in exercise configuration.")


def _requireContainer(exercise):
    c = exercise.get("container", {})
    if not c or not "image" in c or not "mount" in c or not "cmd" in c:
        raise ConfigError("Missing or invalid \"container\" in exercise configuration.")
    return c


def _saveForm(request, course, exercise, post_url, form):
    data,files = form.json_and_files(post_url)
    sdir = create_submission_dir(course, exercise)
    write_submission_file(sdir, "data.json", data)
    for name,uploaded in files.items():
        save_submitted_file(sdir, name, uploaded)
    return _acceptSubmission(request, course, exercise, post_url, sdir)


def _acceptSubmission(request, course, exercise, post_url, sdir):
    '''
    Queues the submission for grading.
    '''
    container_flag = settings.CONTAINER_MODE and "container" in exercise

    # Backup synchronous grading.
    if not container_flag and not settings.CELERY_BROKER:
        LOGGER.warning("No queue configured")
        from grader.runactions import runactions
        r = runactions(course, exercise, sdir, get_uid(request), int(request.GET.get("ordinal_number", 1)))
        html = template_to_str(course, exercise, "", r["template"], r["result"])
        return render_template(request, course, exercise, post_url,
            "access/async_accepted.html", {
                "synchronous": True,
                "accepted": True,
                "max_points": r["result"].get("max_points", 1),
                "points": r["result"].get("points", 0),
                "feedback": html,
            })

    if "submission_url" in request.GET:
        surl = request.GET["submission_url"]
        surl_missing = False
    else:
        LOGGER.warning("submission_url missing from a request")
        surl = request.build_absolute_uri(reverse('test-result'))
        surl_missing = True

    _acceptSubmission.counter += 1

    # Order container for grading.
    if container_flag:
        c = _requireContainer(exercise)
        sid = os.path.basename(sdir)
        write_submission_meta(sid, {
            "url": surl,
            "dir": sdir,
        })
        r = invoke([
            settings.CONTAINER_SCRIPT,
            sid,
            request.scheme + "://" + request.get_host(),
            c["image"],
            os.path.join(DIR, course["key"], c["mount"]),
            sdir,
            c["cmd"],
        ])
        LOGGER.debug("Container order exit=%d out=%s err=%s",
            r["code"], r["out"], r["err"])
        qlen = 1

    # Queue in celery & rabbitmq for chroot sandbox actions.
    else:
        tasks.grade.delay(course["key"], exercise["key"],
            translation.get_language(), surl, sdir, get_uid(request),
            int(request.GET.get("ordinal_number", 1)))
        qlen = queue_length()
        LOGGER.debug("Submission of %s/%s, queue counter %d, queue length %d",
            course["key"], exercise["key"], _acceptSubmission.counter, qlen)
        if qlen >= settings.QUEUE_ALERT_LENGTH:
            LOGGER.error("Queue alert, length: %d", qlen)

    return render_template(request, course, exercise, post_url,
        "access/async_accepted.html", {
            "accepted": True,
            "wait": True,
            "missing_url": surl_missing,
            "queue": qlen
        })

_acceptSubmission.counter = 0
