#!/bin/sh -eu

# Start background services/tasks
#start_services
if [ $USE_GITMANAGER = 'true' ]; then
    run_services aplus-lti-services
    setuidgid $USER python3 manage.py reload_course_configuration --no-reload --url 'http://gitmanager:8070/default/aplus-json' def/current
    setuidgid $USER python3 manage.py reload_course_configuration --no-reload --url 'http://gitmanager:8070/aplus-manual/aplus-json' aplus-manual/master
    setuidgid $USER python3 manage.py reload_course_configuration --no-reload --url 'http://gitmanager:8070/test-course-master/aplus-json' test-course/master
else
    # start course updater (will exit when successful)
    run_services aplus-course-update aplus-lti-services
fi
