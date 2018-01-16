import os, tempfile
from django.core.urlresolvers import reverse
from django.http import HttpResponse, JsonResponse
from django.shortcuts import render, redirect, get_object_or_404

from .forms import CourseRepoForm
from .models import CourseRepo


clean_flag = os.path.join(tempfile.gettempdir(), "mooc-grader-manager-clean")


def repos(request):
    return render(request, 'gitmanager/repos.html', {
        'repos': CourseRepo.objects.all(),
    })


def edit(request, key=None):
    if key:
        repo = get_object_or_404(CourseRepo, key=key)
        form = CourseRepoForm(request.POST or None, instance=repo)
    else:
        repo = None
        form = CourseRepoForm(request.POST or None)
    for name in form.fields:
        form.fields[name].widget.attrs = {'class': 'form-control'}
    if request.method == 'POST' and form.is_valid():
        form.save()
        return redirect('manager-repos')
    return render(request, 'gitmanager/edit.html', {
        'repo': repo,
        'form': form,
    })


def updates(request, key):
    repo = get_object_or_404(CourseRepo, key=key)
    return render(request, 'gitmanager/updates.html', {
        'repo': repo,
        'updates': repo.updates.order_by('-request_time').all(),
        'hook': request.build_absolute_uri(reverse('manager-hook', args=[key])),
    })


def build_log_json(request, key):
    try:
        repo = CourseRepo.objects.get(key=key)
    except CourseRepo.DoesNotExist:
        return JsonResponse({})
    latest_update = repo.updates.order_by("-updated_time")[0]
    return JsonResponse({
        'build_log': latest_update.log_nl(),
        'request_ip': latest_update.request_ip,
        'request_time': latest_update.request_time,
        'updated': latest_update.updated,
        'updated_time': latest_update.updated_time
    })


def get_client_ip(request):
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        return x_forwarded_for.split(',')[0]
    return request.META.get('REMOTE_ADDR')


def hook(request, key):
    repo = get_object_or_404(CourseRepo, key=key)
    if request.method == 'POST':
        if repo.updates.filter(updated=False).count() == 0:
            repo.updates.create(
                course_repo=repo,
                request_ip=get_client_ip(request)
            )

        # Remove clean flag for the cronjob.
        if os.path.exists(clean_flag):
            os.remove(clean_flag)

    if request.META.get('HTTP_REFERER'):
        return redirect('manager-updates', repo.key)

    return HttpResponse('ok')
