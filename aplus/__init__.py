
# Version
try:
    from .version import __version__
except ImportError:
    try:
        __version__ = (
            __import__('subprocess')
                .check_output(('git', 'describe'))
                .decode('utf-8')
                .strip()
                .lstrip('v')
        )
    except Exception as error:
        __import__('warnings').warn(
            'Unable to determine aplus version. %s: %s' % (
                error.__class__.__name__,
                error,
            ))
        __version__ = 'unknown'
