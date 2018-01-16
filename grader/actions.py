'''
Grading actions that can be configured for asynchronous grading tasks.

Functions take arguments:

    @type course: C{dict}
    @param course: course configuration dictionary
    @type exercise: C{dict}
    @param exercise: exercise configuration dictionary
    @type action: C{dict}
    @param action: action configuration dictionary
    @type submission_dir: C{str}
    @param submission_dir: a submission directory where submitted files are stored
    @rtype: C{dict}
    @return: points = granted points, max_points = maximum points,
        out = standard out, err = standard error,
        stop = True to stop further actions, appendix = appendix output
'''
from django.conf import settings
from access.config import ConfigError
from access.types.forms import GradedForm
from util.files import read_submission_file
from util.http import get_json
from util.personalized import user_personal_directory_path, select_generated_exercise_instance
from util.shell import invoke_script, invoke_sandbox
from util.templates import template_to_str
from util.xslt import transform
import logging, json

LOGGER = logging.getLogger('main')


def prepare(course, exercise, action, submission_dir, user_ids='', submission_number=1):
    '''
    Runs the preparation script for the submitted files.

    @type user_ids: C{str}
    @param user_ids: user ID(s) of the submitter(s) as string (format "1", "1-2-3")
    @type submission_number: C{int}
    @param submission_number: ordinal number of the submission
    '''
    args = {
        "course_key": course["key"],
        "exercise_key": exercise["key"],
    }
    cp_personal_error = None
    if "personalized" in exercise and exercise["personalized"]:
        args["userid"] = user_ids
        args["gen_instance_path"] = select_generated_exercise_instance(course, exercise, user_ids, submission_number)
        if not settings.ENABLE_PERSONAL_DIRECTORIES and "cp_personal" in action:
            cp_personal_error = 'settings.ENABLE_PERSONAL_DIRECTORIES is False but action grader.actions.prepare has "cp_personal" field'
            LOGGER.error(cp_personal_error)

    result = _boolean(invoke_script(settings.PREPARE_SCRIPT,
        _collect_args(("attachment_pull", "attachment_unzip", "unzip",
            "charset", "cp_exercises", "cp", "mv", "cp_personal", "cp_generated"),
            action, args),
        submission_dir))
    if cp_personal_error:
        # add the error to the feedback too
        result["err"] += "\n" + cp_personal_error
    return result


def gitclone(course, exercise, action, submission_dir):
    '''
    Runs a git clone script.
    '''
    return _appendix(_boolean(invoke_script(settings.GITCLONE_SCRIPT,
        _collect_args(("repo_dir", "read", "files"), action), submission_dir)))


def sandbox(course, exercise, action, submission_dir):
    '''
    Executes sandbox script and looks for TotalPoints line in the result.
    '''
    return _find_point_lines(invoke_sandbox(course["key"], action,
        submission_dir))


def sandbox_python_test(course, exercise, action, submission_dir):
    '''
    Executes sandbox script and looks for succesful python test. Test may print
    out TotalPoints and MaxPoints lines at end.
    '''
    r = sandbox(course, exercise, action, submission_dir)
    return { "points": r["points"], "max_points": r["max_points"],
        "out": r["err"], "err": "", "stop": r["stop"] }


def without_sandbox(course, exercise, action, submission_dir):
    '''
    Executes script outside the sandbox and looks for TotalPoints line in the result.
    '''
    return _find_point_lines(invoke_sandbox(course["key"], action,
        submission_dir, without_sandbox=True))

def expaca(course, exercise, action, submission_dir):
    '''
    Executes third party expaca testing application.
    '''
    r = invoke_script(settings.EXPACA_SCRIPT,
        _collect_args(("rule_file", "model_dir", "user_dir"), action),
        submission_dir)

    # Expaca should always return 0.
    if r["code"] != 0:
        raise ConfigError("Expaca return code not zero!\nMore information: %s"
            % (str(r)))
    out = r["out"]
    points = 0
    max_points = 0

    # Find points in the XML.
    b = out.find("<TotalPoints>")
    if b >= 0:
        e = out.find("</TotalPoints>", b + 13)
        points = int(out[b + 13 : e])
    b = out.find("<TotalMaxpoints>")
    if b >= 0:
        e = out.find("</TotalMaxpoints>", b + 16)
        max_points = int(out[b + 16 : e])

    # Transform the feedback if configured.
    if "xslt_transform" in action:
        out = transform(out, "%s/%s" % (settings.BASE_DIR,
            action["xslt_transform"]))

    return { "points": points, "max_points": max_points, "out": out,
        "err": r["err"], "stop": False }


def store_user_files(course, exercise, action, submission_dir, user_ids, submission_number=1):
    '''
    Stores files from the submission directory to the personal directory of the user(s).
    '''
    if not (settings.ENABLE_PERSONAL_DIRECTORIES and \
            "personalized" in exercise and exercise["personalized"]):
        msg = 'Action "grader.actions.store_user_files" can only be used in personalized exercises. ' \
            'Check project settings.ENABLE_PERSONAL_DIRECTORIES value and exercise-specific personalization configuration.'
        LOGGER.error(msg)
        raise ConfigError(msg)
    args = {
        "target": user_personal_directory_path(course, exercise, user_ids),
    }

    return _boolean(invoke_script(settings.STORE_USER_FILES_SCRIPT,
        _collect_args(("cp",),
            action, args),
        submission_dir))


def timeout(course, exercise, action, submission_dir):
    '''
    FOR DEBUG: Sleeps for a long time to test grading time out.
    '''
    import time
    print("stdasync.timeoutAction: Sleeping and blocking queue for testing purposes.")
    time.sleep(15 * 60)
    return { "points": 10, "out": "Did not reach timeout, should not happen.", "err": "", "stop": True }


def gitlabquery(course, exercise, action, submission_dir):
    '''
    Queries gitlab API to check repository properties.
    '''
    if not "require_gitlab" in exercise:
        raise ConfigError("This action needs require_gitlab in exercise.")
    if not "token" in action:
        raise ConfigError("Token missing from configuration for gitlab privacy check.")
    url = None
    err = ""
    try:
        with open(submission_dir + "/user/gitsource") as content:
            source = content.read()
        try:
            from urllib.parse import quote_plus
        except ImportError:
            from urllib import quote_plus
        rid = quote_plus(source[source.index(":") + 1:])
        url = "https://%s/api/v3/projects/%s?private_token=%s" % (exercise["require_gitlab"], rid, action["token"])
        data = get_json(url)
        if "private" in action and action["private"] and data["public"]:
            err = "%s has public access in settings! Remove it to grade exercises." % (data["web_url"])
        if "forks" in action:
            if not "forked_from_project" in data or \
                data["forked_from_project"]["path_with_namespace"] != action["forks"]:
                err = "%s is not forked from %s." % (data["web_url"], action["forks"])
    except Exception:
        LOGGER.exception("Failed to check gitlab URL: %s", url)
    return { "points": 0, "max_points": 0, "out": "", "err": err, "stop": err != "" }


def resubmit_form(course, exercise, action, submission_dir):
    data = json.loads(read_submission_file(submission_dir, "data.json"))
    form = GradedForm(data, exercise=exercise)
    out = template_to_str(course, exercise, data.get("__aplus_post_url"), "access/task_resubmit.html", {
        "form": form,
        "instructions": action.get("instructions", False),
    })
    return { "points": 0, "max_points": 0, "out": out, "err": "", "stop": False }


def _collect_args(arg_names, action, args={}):
    '''
    Collects argument map for names in action.
    '''
    for name in arg_names:
        if name in action:
            args[name] = action[name]
    return args


def _boolean(result):
    '''
    Plain return code check for continuing actions.
    '''
    return { "points": 0, "max_points": 0, "out": result["out"],
        "err": result["err"], "stop": result["code"] != 0 }


def _find_point_lines(result):
    '''
    Looks for TotalPoints and/or MaxPoints line in the result.
    '''
    lines = []
    points = 0
    max_points = 0

    # Try to find the point lines.
    for l in result["out"].split("\n"):
        try:
            if l.startswith("TotalPoints: "):
                points = int(l[13:])
            elif l.startswith("MaxPoints: "):
                max_points = int(l[11:])
            else:
                lines.append(l)
        except ValueError:
            pass

    return { "points": points, "max_points": max_points,
        "out": "\n".join(lines), "err": result["err"],
        "stop": result["code"] != 0 }


def _appendix(result):
    '''
    Looks for appendix section in output.
    '''
    out = []
    appendix = []
    in_appendix = False
    for l in result["out"].split("\n"):
        if l == "***APPENDIX***":
            in_appendix = True
        elif in_appendix:
            appendix.append(l)
        else:
            out.append(l)
    result["out"] = "\n".join(out)
    result["appendix"] = "\n".join(appendix)
    return result
