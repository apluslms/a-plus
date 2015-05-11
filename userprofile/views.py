# Django
from django.http import HttpResponse
from django.shortcuts import render_to_response
from django.template.context import RequestContext
from django.contrib.auth.decorators import login_required

# A+
from userprofile.models import StudentGroup

@login_required
def view_groups(request):
    '''
    Displays the student groups available in the system.
    TODO: The students are not able to create new groups or join or quit groups.

    @param request: the HttpRequest object from Django
    '''

    groups          = StudentGroup.objects.all()
    context         = RequestContext(request, {"groups": groups})
    return render_to_response("userprofile/view_groups.html", context)

