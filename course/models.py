# Python
import logging
import urllib, urllib2
from datetime import datetime

# Django
from django.db import models
from django.core.urlresolvers import reverse
from django.db.models import Q
from django.core.validators import RegexValidator
from django.utils.translation import ugettext_lazy as _ 
from django.contrib.contenttypes import generic

# A+
from userprofile.models import UserProfile
from apps.models import BaseTab, BasePlugin

# Course class
class Course(models.Model):
    '''
    Course model represents a course in a university. A course has a name and an
    identification number. It also has a URL which is included in the addresses
    of pages under the course. 
    '''
    
    # Basic information
    name        = models.CharField(max_length=255)
    code        = models.CharField(max_length=255)
    
    # A portion that is included in the addresses under this course
    url         = models.CharField(
                       unique=True,
                       max_length=255,
                       blank=False,
                       validators=[RegexValidator(regex="^[\w\-\.]*$")],
                       help_text="Input an identifier for this course's URL.")
    
    # Relations
    teachers    = models.ManyToManyField(UserProfile,
                                            related_name=u"teaching_courses",
                                            blank=True)
    
    def get_absolute_url(self):
        '''
        Returns the relative URL to this course.
        '''
        return reverse("course.views.view_course", kwargs={"course_url": self.url})
    
    def add_teacher(self, userprofile):
        """ 
        Adds a new teacher to this course. Teachers are also teachers in all course 
        instances that belong to this course. 
        
        @param userprofile: the user profile to add as a teacher
        """
        self.teachers.add(userprofile)
    
    def is_teacher(self, profile):
        return profile in self.teachers.all()

    def get_visible_open_instances(self, profile=None):
        if profile:
            visible_open_instances = []
            for i in self.instances.filter(ending_time__gte=datetime.now()):
                if i.is_visible_to(profile):
                    visible_open_instances.append(i)
        else:
            visible_open_instances = list(self.instances.filter(
                ending_time__gte=datetime.now(), visible_to_students=True))

        return visible_open_instances
    
    def get_breadcrumb(self):
        """
        Returns a list of tuples containing the names and url 
        addresses of parent objects and self. 
        """
        crumb_tuple = (str(self), self.get_absolute_url())
        return [crumb_tuple]
    
    def __unicode__(self):
        '''
        Returns a short representation of the course as an unicode string.
        '''
        return self.code + u" " + self.name


class CourseInstance(models.Model):
    """ 
    CourseInstance class represent an instance of a course. A single course may have 
    several instances either at the same time or during different years. All instances 
    have the same teacher, but teaching assistants and students are connected to individual 
    instances.
    """
    
    # Basic information
    instance_name           = models.CharField(max_length=255)
    website                 = models.URLField(max_length=255, blank=True)
    
    url = models.CharField(
            unique=False,
            max_length=255,
            blank=False,
            validators=[RegexValidator(regex="^[\w\-\.]*$")],
            help_text="Input an URL identifier for this course.")
    
    starting_time           = models.DateTimeField()
    ending_time             = models.DateTimeField()

    visible_to_students     = models.BooleanField(default=True)
    
    # Relations
    assistants              = models.ManyToManyField(UserProfile,
                                                     related_name=u"assisting_courses", 
                                                     blank=True)
    course                  = models.ForeignKey(Course, related_name=u"instances")
    
    plugins                 = generic.GenericRelation(BasePlugin, object_id_field="container_pk", content_type_field="container_type")
    tabs                    = generic.GenericRelation(BaseTab, object_id_field="container_pk", content_type_field="container_type")

    def is_assistant(self, profile):
        """
        Returns True if the given profile belongs to an assistant on this course instance.
        Otherwise returns False.
        """
        return profile in self.assistants.all()
    
    def is_teacher(self, profile):
        """
        Returns True if the given profile belongs to a teacher of this course.
        """
        return self.course.is_teacher(profile)
    
    def is_staff(self, profile):
        """
        Returns True if the given profile belongs to an assistant of this course instance
        or a teacher of this course. Otherwise returns False.
        """
        return self.is_assistant(profile) or self.is_teacher(profile)
    
    def get_course_staff(self):
        """ 
        Returns a QuerySet of UserProfile models of the teachers and 
        assistants for this course instance. 
        """
        query = Q(teaching_courses=self.course) | Q(assisting_courses=self)
        return UserProfile.objects.filter(query).distinct()

    def get_students(self):
        return UserProfile.objects.filter(submissions__exercise__course_module__course_instance=self).distinct()
    
    def add_assistant(self, user):
        """ 
        Adds the given user as a course assistant to this instance. 
        """
        self.assistants.add(user.get_profile())
    
    def is_open(self):
        """ 
        Returns True if this course instance is currently open. Otherwise False. 
        """
        return self.starting_time <= datetime.now() <= self.ending_time

    def is_visible_to(self, profile=None):
        if profile:
            return (self.visible_to_students
                    or self.is_staff(profile)
                    or profile.is_staff())
        else:
            return self.visible_to_students
    
    def get_absolute_url(self):
        '''
        Returns the URL to this CourseInstance's dashboard.
        '''
        return reverse("course.views.view_instance", kwargs={"course_url": self.course.url, 
                                                             "instance_url": self.url})
    
    def get_results_url(self):
        '''
        Returns the URL to this CourseInstance's results page.
        '''
        return reverse("course.views.view_instance_results", kwargs={"course_url": self.course.url, 
                                                                     "instance_url": self.url})
    
    def get_breadcrumb(self):
        """ 
        Returns a list of tuples containing the names and url 
        addresses of parent objects and self. 
        """
        crumb       = self.course.get_breadcrumb()
        crumb_tuple = (self.instance_name, self.get_absolute_url())
        crumb.append(crumb_tuple)
        return crumb
    
    def get_label(self):
        '''
        Returns the label which to display on the dashboard tab.
        @deprecated: the label behavior will be removed
        '''
        return _("Dashboard")
    
    def __unicode__(self):
        return self.course.code + u": " + self.instance_name
    
    class Meta:
        unique_together = ("course", "url")

class CourseHook(models.Model):
    """
    Provides a hook for a course instance, that is called after a certain
    action. Currently only hook implemented is post-grading, i.e. after a
    student submission has been succesfully graded by the external service.

    When a hook is triggered it will do a HTTP POST to a defined URL
    passing along data (e.g. submission id).
    """

    HOOK_CHOICES = (
        ("post-grading", "Post grading"),
    )

    hook_url = models.URLField(verify_exists=False)
    hook_type = models.CharField(max_length=12,
        choices=HOOK_CHOICES,
        default="post-grading")
    course_instance = models.ForeignKey(CourseInstance,
        related_name="course_hook")


    def trigger(self, data):
        logger = logging.getLogger("plus.hooks")
        try:
            res = urllib2.urlopen(self.hook_url,
                urllib.urlencode(data), timeout=10)
            logger.info('%s postend to %s on %s with %s',
                self.hook_type, self.hook_url, self.course_instance, data
                )
        except:
            logger.error(
                "HTTP POST failed on %s hook to %s (%s)",
                self.hook_type,
                self.hook_url,
                self.course_instance)

    def __unicode__(self):
        return "%s -> %s" % (self.course_instance, self.hook_url)

def get_visible_open_course_instances(profile=None):
    if profile:
        visible_open_instances = []
        for i in CourseInstance.objects.filter(ending_time__gte=datetime.now()):
            if i.is_visible_to(profile):
                visible_open_instances.append(i)
    else:
        visible_open_instances = list(CourseInstance.objects.filter(
            ending_time__gte=datetime.now(), visible_to_students=True))

    return visible_open_instances
