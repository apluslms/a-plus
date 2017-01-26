from django.http import UnreadablePostError

def skip_unreadable_post(record):
    """ Skips log records of unfinished post requests. """
    if record.exc_info:
        exc_type, exc_value = record.exc_info[:2]
        if isinstance(exc_value, UnreadablePostError):
            return False
    return True
