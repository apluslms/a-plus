from django.shortcuts import render

# pylint: disable-next=unused-argument
def error_404(request, exception=None):
    context = {
        'show_language_toggle': True,
    }
    return render(request, '404.html', context, status=404)

# pylint: disable-next=unused-argument
def error_403(request, exception=None):
    context = {
        'show_language_toggle': True,
    }
    return render(request, '403.html', context, status=403)

# pylint: disable-next=unused-argument
def error_500(request, exception=None):
    context = {
        'show_language_toggle': True,  
    }
    return render(request, '500.html', context, status=500)
