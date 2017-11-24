import uuid
import requests
import json

from django.core.urlresolvers import reverse


def statement_graded(request, user, submission):
    exercise = submission.exercise
    return {
        "id": str(uuid.uuid1()),
        "actor": statement_actor(request, user),
        "verb": {
            "id": "http://adlnet.gov/expapi/verbs/completed",
            "display": { "en": "completed" },
        },
        "object": statement_object(request, exercise),
        "result": {
              "completion": True,
              "response": json.dumps(submission.submission_data),
              "score": {
                    "max": exercise.max_points,
                    "min": 0,
                    "raw": submission.grade,
                    "scaled": submission.grade / exercise.max_points,
              }
        }
    }


def statement_answered(request, user, submission):
    exercise = submission.exercise
    return {
        "id": str(uuid.uuid1()),
        "actor": statement_actor(request, user),
        "verb": {
            "id": "http://adlnet.gov/expapi/verbs/answered",
            "display": { "en": "answered" },
        },
        "object": statement_object(request, exercise),
        "result": {
              "completion": submission.status in ('ready', 'unofficial'),
              "response": json.dumps(submission.submission_data),
              "score": {
                    "max": exercise.max_points,
                    "min": 0,
                    "raw": submission.grade,
                    "scaled": submission.grade / exercise.max_points,
              }
        }
    }


def statement_viewed(request, user, exercise):
    return {
        "id": str(uuid.uuid1()),
        "actor": statement_actor(request, user),
        "verb": {
            "id": "http://id.tincanapi.com/verb/viewed",
            "display": { "en": "viewed" },
        },
        "object": statement_object(request, exercise),
    }


def statement_actor(request, user):
    return {
        #"account": {
        #    "name": user.id,
        #    "homePage": uri(request, reverse('home')),
        #},
        "name": "{} {}".format(user.first_name, user.last_name),
        "mbox": "mailto:{}".format(user.email),
        "objectType": "Agent",
    }


def statement_object(request, exercise):
    return {
        "id": uri(request, exercise.get_absolute_url()),
        "definition": {
            "name": { "en": str(exercise) },
            "description": { "en": exercise.description },
            "type": "https://apluslms.github.io/type/a-plus/exercise",
        },
    }


def uri(request, path):
    if request:
        return request.build_absolute_uri(path)
    return path
