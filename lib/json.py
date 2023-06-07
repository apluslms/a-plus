from typing import Any, Type
from json import JSONEncoder

from django.core.serializers.json import DjangoJSONEncoder
from django.http import HttpRequest, JsonResponse
from django.shortcuts import render

from exercise.models import ExercisePage, Submission


class AJAXJSONEncoder(DjangoJSONEncoder):
    """Custom JSON encoder to implement encoding of our own types.

    The purpose is different from the API serializers: this is meant for
    returning specialized data about the object that is used in the site
    javascript, instead of just serializing the object.
    """
    def default(self, obj: Any) -> Any:
        if isinstance(obj, Submission):
            return {
                "id": obj.id,
                "poll_url": obj.get_url("submission-poll"),
                "ready_url": obj.get_url(
                    getattr(self, "submission_poll_ready_url_name", "submission")
                ),
            }
        elif isinstance(obj, ExercisePage):
            return {
                "content": obj.content,
                "errors": obj.errors,
            }

        return super().default(obj)


def json_response_with_messages(
        request: HttpRequest,
        data: dict,
        encoder: Type[JSONEncoder] = AJAXJSONEncoder,
        *args,
        **kwargs,
        ) -> JsonResponse:
    data["messages"] = {
        "selector": ".site-messages",
        "html": render(request, "_messages.html").content.decode(),
    }

    return JsonResponse(data, encoder, *args, **kwargs)
