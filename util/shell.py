'''
Utility functions to handle shell processes.

'''
from django.conf import settings
from access.config import ConfigError
import subprocess
import logging


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
    p = subprocess.Popen(cmd_list, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    out, err = p.communicate()
    return {"code": p.returncode, "out": out.strip(), "err": err.strip()}


def invoke_script(name, arguments, dirarg=None):
    '''
    Invokes a grader script.

    @type name: C{str}
    @param name: a script file name
    @type net: C{bool}
    @param net: True to add network enabled argument
    @type arguments: C{dict}
    @param arguments: arguments to pass for the script
    @type dirarg: C{str}
    @param dirarg: a submission directory to grade
    @rtype: C{dict}
    @return: code = process return code, out = standard out, err = standard error
    '''
    cmd = ["%s/%s" % (settings.BASE_DIR, name)]
    for key, value in arguments.iteritems():
        cmd.append("--%s" % (key))
        cmd.append("%s" % (value))
    if dirarg is not None:
        cmd.append("--dir")
        cmd.append(dirarg)
    return invoke(cmd)


def invoke_configured_sandbox(action, dirarg=None):
    '''
    Invokes a configured grader script in a sandboxed environment.

    @type action: C{dict}
    @param action: action configuration
    @type dirarg: C{str}
    @param dirarg: a submission directory to grade
    @rtype: C{dict}
    @return: code = process return code, out = standard out, err = standard error
    '''
    if not "cmd" in action or not isinstance(action["cmd"], list):
        raise ConfigError("Missing list \"cmd\" from action configuration")
    cmd = [ "%s/scripts/chroot_execvp" % (settings.BASE_DIR)]

    if "net" in action and action["net"]:
        cmd.append("net")

    for key in ("time", "memory", "files", "disk"):
        if key in action:
            cmd.append(action[key])
        else:
            cmd.append(settings.SANDBOX_LIMITS[key])

    if dirarg:
        cmd.append(dirarg)
    else:
        cmd.append("-")
    cmd.extend(action["cmd"])
    return invoke(cmd)
