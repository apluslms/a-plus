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
    @rtype: C{tuple}
    @return: points = granted points, out = standard out, err = standard error, stop = True to stop further actions

'''
from django.conf import settings
from access.config import ConfigError
from util.shell import invoke_configured_sandbox, invoke_script
from util.xslt import transform
from util.http import get_json
import logging

LOGGER = logging.getLogger('main')


def prepare(course, exercise, action, submission_dir):
    '''
    Runs the preparation script for the submitted files.

    '''
    return _run_boolean("/scripts/prepare.sh", ("charset", "add", "unzip", "attachment", "pull", "mv"), action, submission_dir)


def gitclone(course, exercise, action, submission_dir):
    '''
    Runs a git clone script.

    '''
    return _appendix(_run_boolean("/scripts/gitclone.sh", ("read", "files"), action, submission_dir))


def sandbox(course, exercise, action, submission_dir):
    '''
    Executes sandbox script and looks for TotalPoints line in the result.

    '''
    return _find_point_lines(invoke_configured_sandbox(action, submission_dir))


def sandbox_python_test(course, exercise, action, submission_dir):
    '''
    Executes sandbox script and looks for succesful python test. Test may print
    out TotalPoints and MaxPoints lines at end.

    '''
    r = _find_point_lines(invoke_configured_sandbox(action, submission_dir))
    return { "points": r["points"], "max_points": r["max_points"], "out": r["err"], "err": "", "stop": r["stop"] }


def expaca(course, exercise, action, submission_dir):
    '''
    Executes script and looks for expaca XML result.

    '''
    name = "scripts/expaca_grade.sh"
    if "attachment" in action and action["attachment"]:
        name = "scripts/expaca_attachment_grade.sh"
    args = {}
    for key in ("testdir", "rulefile", "modeldir", "filesdir"):
        if key in action:
            args[key] = action[key]
    r = invoke_script(name, args, submission_dir)

    # Expaca should return 0.
    if r["code"] != 0:
        raise ConfigError("Expaca return code not zero!\nMore information: %s" % (str(r)))

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
        out = transform(out, "%s/%s" % (settings.BASE_DIR, action["xslt_transform"]))

    return { "points": points, "max_points": max_points, "out": out, "err": r["err"], "stop": False }


def timeout(course, exercise, action, submission_dir):
    '''
    FOR DEBUG: Sleeps for a long time to test grading time out.

    '''
    import time
    print "stdasync.timeoutAction: Sleeping and blocking queue for testing purposes."
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
        import urllib
        rid = urllib.quote_plus(source[source.index(":") + 1:])
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


def _run_boolean(script_name, arg_names, action, submission_dir):
    '''
    Collects argument map for names in action.

    @type script_name: C{str}
    @param script_name: a script name
    @type arg_names: C{list}
    @param arg_names: argument names
    @type action: C{dict}
    @param action: action configuration
    @rtype: C{dict}
    @return: points = granted points, out = standard out, err = standard error, stop = True to stop further actions
    '''
    args = {}
    for name in arg_names:
        if name in action:
            args[name] = action[name]
    r = invoke_script(script_name, args, submission_dir)
    return { "points": 0, "max_points": 0, "out": r["out"], "err": r["err"], "stop": r["code"] != 0 }


def _find_point_lines(result):
    '''
    Looks for TotalPoints and/or MaxPoints line in the result.

    @type result: C{dict}
    @param result: a shell invocation result
    @rtype: C{dict}
    @return: points = granted points, out = standard out, err = standard error, stop = True to stop further actions
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

    return { "points": points, "max_points": max_points, "out": "\n".join(lines),
             "err": result["err"], "stop": result["code"] != 0 }


def _appendix(result):
    '''
    Looks for appendix section in output.

    @type result: C{dict}
    @param result: a shell invocation result
    @rtype: C{dict}
    @return: points = granted points, out = standard out, err = standard error, stop = True to stop further actions, appendix = appendix output
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
