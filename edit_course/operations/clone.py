import logging

from django.db import transaction
from django.contrib.auth.models import User
from course.models import CourseInstance
from course.sis import get_sis_configuration, StudentInfoSystem

logger = logging.getLogger("aplus.course")

def set_sis(instance: CourseInstance, id: str, enroll: bool) -> None: # pylint: disable=redefined-builtin
    """
    Set teachers, starting time and ending based on Student Information System.

    Parameters
    ----------
    instance
        The course instance to be modified

    id
        Course realisation identifier used by the SIS system

    enroll
        Boolean value indicating whether or not students
        from the local organization must enroll through SIS
    """
    sis: StudentInfoSystem = get_sis_configuration()
    if not sis:
        # Student Info System not configured
        return
    try:
        coursedata = sis.get_course_data(id)
    except Exception:
        logger.exception("Error getting course data from SIS.")
        return

    if coursedata.get('starting_time') and coursedata.get('ending_time'):
        instance.starting_time = coursedata['starting_time']
        instance.ending_time = coursedata['ending_time']

    instance.sis_id = id
    instance.sis_enroll = enroll
    instance.save()

    if coursedata['teachers']:
        for i in coursedata['teachers']:
            try:
                user = User.objects.get(username=i)
            except User.DoesNotExist:
                # If user does not exist, create a new user.
                # If external authentication (e.g. Shibboleth) is used, other
                # attributes will be updated when user logs in for the first time.
                user = User.objects.create_user(i)

            instance.add_teacher(user.userprofile)

@transaction.atomic
def clone( # pylint: disable=too-many-locals too-many-arguments
        cloner,
        instance,
        url,
        name,
        clone_teachers,
        clone_assistants,
        clone_usertags,
        clone_menuitems,
        siskey,
        sisenroll,
):
    """
    Clones the course instance and returns the new saved instance.
    """
    teachers = list(instance.teachers.all())
    assistants = list(instance.assistants.all())
    usertags = list(instance.usertags.all())
    menuitems = list(instance.ext_services.all())

    # Save as new course instance.
    instance.id = None
    instance.visible_to_students = False
    instance.configure_url = ""
    instance.url = url
    instance.instance_name = name
    instance.sis_id = ''
    instance.sis_enroll = False
    instance.save()

    if clone_teachers:
        instance.set_teachers(teachers)
    # The cloned course instance has at least one teacher, which is the cloning user
    instance.add_teacher(cloner)

    if clone_assistants:
        instance.set_assistants(assistants)

    if siskey and siskey != 'none':
        set_sis(instance, siskey, sisenroll)

    if clone_usertags:
        for usertag in usertags:
            usertag.id = None
            usertag.course_instance = instance
            usertag.save()

    if clone_menuitems:
        for menuitem in menuitems:
            menuitem.id = None
            menuitem.course_instance = instance
            menuitem.save()

    return instance
