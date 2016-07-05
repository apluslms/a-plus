from hashlib import md5
from django.conf import settings


def detect_user(request):
    '''
    Tries to detect userid from the request.
    '''
    user = request.GET.get("user", None)

    # Check submission_url for A+ userid.
    if not user and "submission_url" in request.GET:
        parts = request.GET["submission_url"].partition("/rest/exercise/")[2].split("/")
        if len(parts) > 4 and parts[1] == "students":
            return parts[2].split("-")[0]

    if user:
        return user.strip()
    return user


def make_hash(secret, user):
    '''
    Creates a hash key for a user.
    '''
    if user is not None:
        coded = secret + user
        return md5(coded.encode('ascii', 'ignore')).hexdigest()
    return None


def get_uid(request):
    '''
    Returns the user ID value(s) as string from the request.
    Based on the new uid GET query parameter that was added to the A+ grader protocol
    in April 2016.
    '''
    user_ids = request.GET.get("uid", "")
    # format: "1" for one user, "1-2-3" for many
    
    if not user_ids and settings.DEBUG:
        # in debug mode, set a default id if the URL has no GET query parameter
        user_ids = "1"
        
    return user_ids


def user_ids_from_string(user_ids_str):
    '''
    Given a string of user IDs (in the format "1-2-3"), return a list of the
    user IDs as integers.
    '''
    return list(map(lambda uid: int(uid), user_ids_str.split('-')))
