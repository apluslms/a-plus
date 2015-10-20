'''
Utility functions to handle shell processes.

'''
from django.conf import settings
from access.config import ConfigError
import subprocess
import logging
import os.path


LOGGER = logging.getLogger('main')


def invoke(cmd_list):
    '''
    Invokes a shell command.

    @type cmd_list: C{list}
    @param cmd_list: command line arguments
    @rtype: C{dict}
    @return: code = process return code, out = standard out, err = standard error
    '''
    LOGGER.debug('Subprocess %s', cmd_list)
    p = subprocess.Popen(cmd_list, universal_newlines=True,
        stdout=subprocess.PIPE, stderr=subprocess.PIPE)
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


def invoke_sandbox(course_key, action, dirarg=None):
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

    cmd = [ settings.SANDBOX_RUNNER if os.path.isfile(settings.SANDBOX_RUNNER)
        else settings.SANDBOX_FALLBACK ]

    if "net" in action and action["net"]:
        cmd.append("net")

    for key in ("time", "memory", "files", "disk"):
        if key in action:
            cmd.append(str(action[key]))
        else:
            cmd.append(str(settings.SANDBOX_LIMITS[key]))

    if dirarg:
        cmd.append(os.path.join(dirarg,
            action["dir"] if "dir" in action else "user"))
    else:
        cmd.append("-")
    cmd.append(course_key)
    cmd.extend(action["cmd"])
    return invoke(cmd)
