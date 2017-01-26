from lib.crypto import get_signed_message


GRADER_AUTH_TOKEN = 'token'


def get_graderauth_submission_params(submission):
    token = "s{:x}.{}".format(submission.id, submission.hash)
    return [(GRADER_AUTH_TOKEN, token)]


def get_graderauth_exercise_params(exercise, user=None):
    user_id = str(user.id) if user else ''
    identifier = "{:s}.{:d}".format(user_id, exercise.id)
    message = get_signed_message(identifier).decode('ascii')
    token = "e{:s}".format(message)
    return [(GRADER_AUTH_TOKEN, token)]
