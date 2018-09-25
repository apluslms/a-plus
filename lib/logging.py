from django.http import UnreadablePostError

def skip_unreadable_post(record):
    """Skips log records of unfinished post requests."""
    return not record.exc_info or not issubclass(record.exc_info[0], UnreadablePostError)
