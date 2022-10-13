import requests
from django.http import HttpResponse
from django.shortcuts import render
from django.urls import reverse
from django.utils.safestring import mark_safe


def first(request):

    if request.method == "POST":
        submission = request.POST.get("answer", "").lower()
        points = 0
        if 'hello' in submission:
            points += 1
        if 'a+' in submission:
            points += 1
        return render(request, "exercises/first_result.html", {
            "points": points,
            "max_points": 2,
        })

    return render(request, "exercises/first_exercise.html")


def file(request):

    if request.method == "POST":
        if "myfile" in request.FILES and request.FILES["myfile"].name:
            status = "accepted"
        else:
            status = "error"
        return render(request, "exercises/file_result.html", {
            "status": status,
        })

    return render(request, "exercises/file_exercise.html")


def ajax(request):

    def parse_int(s):
        try:
            return int(s)
        except Exception:
            return 0

    if request.method == "POST":
        points = parse_int(request.POST.get("points"))
        max_points = parse_int(request.POST.get("max_points"))
        url = request.GET.get("submission_url")

        def respond_text(text):
            response = HttpResponse(text)
            response["Access-Control-Allow-Origin"] = "*"
            return response

        if not url:
            return respond_text('{ "errors": ["Missing submission_url"] }')

        response = requests.post(url, timeout=3, data={
            "points": points,
            "max_points": max_points,
            "feedback": "You got {} / {} points for your answer.".format(points, max_points),
            "grading_payload": "{}",
        })
        return respond_text(response.text)

    return render(request, "exercises/ajax_exercise.html", {
        "url": mark_safe(
            request.build_absolute_uri("{}?{}".format(
                reverse("ajax"), request.META.get("QUERY_STRING", "")
            ))
        ),
    })
