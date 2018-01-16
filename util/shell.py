'''
Utility functions to handle shell processes.

'''
from django.conf import settings
from access.config import ConfigError
import subprocess
import logging
import os.path


LOGGER = logging.getLogger('main')


def invoke(cmd_list, cwd=None):
    '''
    Invokes a shell command.

    @type cmd_list: C{list}
    @param cmd_list: command line arguments
    @type cwd: C{str}
    @param cwd: set current working directory for the command, None if not used
    @rtype: C{dict}
    @return: code = process return code, out = standard out, err = standard error
    '''
    LOGGER.debug('Subprocess %s', cmd_list)
    p = subprocess.Popen(cmd_list, universal_newlines=True,
        stdout=subprocess.PIPE, stderr=subprocess.PIPE, cwd=cwd)
    out, err = p.communicate()
    return {"code": p.returncode, "out": out.strip(), "err": err.strip()}


def invoke_script(script, arguments, dirarg=None):
    '''
    Invokes a named shell script.

    @type script: C{str}
    @param script: a script file name
    @type arguments: C{dict}
    @param arguments: arguments to pass for the script
    @type dirarg: C{str}
    @param dirarg: a submission directory to grade
    @rtype: C{dict}
    @return: code = process return code, out = standard out, err = standard error
    '''
    cmd = [ script ]
    for key, value in arguments.items():
        cmd.append("--%s" % (key))
        cmd.append("%s" % (value))
    if dirarg is not None:
        cmd.append("--dir")
        cmd.append(dirarg)
    return invoke(cmd)


def invoke_sandbox(course_key, action, dirarg=None, without_sandbox=False):
    '''
    Invokes a configured command in the sandbox environment.

    @type action: C{dict}
    @param action: action configuration
    @type dirarg: C{str}
    @param dirarg: a submission directory to grade
    @rtype: C{dict}
    @return: code = process return code, out = standard out, err = standard error
    '''
    if not "cmd" in action or not isinstance(action["cmd"], list):
        raise ConfigError("Missing list \"cmd\" from action configuration")

    if not without_sandbox and os.path.isfile(settings.SANDBOX_RUNNER):
        cmd = [ settings.SANDBOX_RUNNER ]
    else:
        cmd = [ settings.SANDBOX_FALLBACK ]

    if "net" in action and (action["net"] is True or str(action["net"]).lower() in ('true','yes')):
        cmd.append("net")

    for key in ("time", "memory", "files", "disk"):
        if key in action:
            cmd.append(str(action[key]))
        else:
            cmd.append(str(settings.SANDBOX_LIMITS[key]))

    if dirarg:
        if "dir" in action:
            if action["dir"] == ".":
                cmd.append(dirarg)
            else:
                cmd.append(os.path.join(dirarg, action["dir"]))
        else:
            cmd.append(os.path.join(dirarg, "user"))
    else:
        cmd.append("-")
    cmd.append(course_key)

    if without_sandbox:
        cmd.append("without_sandbox")

    cmd.extend(action["cmd"])

    return invoke(cmd)
