from django.conf.urls import patterns, url

urlpatterns = patterns('',
    url(r'^$', 'access.views.index'),
    url(r'^queue-length$', 'access.views.queue_length'),
    url(r'^test-result$', 'access.views.test_result'),
    url(r'^ajax/([\w-]+)/([\w-]+)$', 'access.views.exercise_ajax'),
    url(r'^([\w-]+)/$', 'access.views.course'),
    url(r'^([\w-]+)/aplus-json$', 'access.views.aplus_json'),
    url(r'^([\w-]+)/([\w-]+)$', 'access.views.exercise'),
    url(r'^([\w-]+)/([\w-]+)/([\d-]+)/generatedfile/([\w-]+)$', 'access.views.generated_exercise_file',
        name='generated-file'),
)
