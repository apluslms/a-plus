# Python
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
    name                = models.CharField(max_length=30)
    code                = models.CharField(max_length=30)
    
    # A portion that is included in the addresses under this course
    url                 = models.CharField(unique=True, max_length=16, blank=False, 
                                           validators=[RegexValidator(regex="^[\w\-\.]*$")],
                                           help_text="Input an identifier for this course's URL.")
    
    # Relations
    teachers            = models.ManyToManyField(UserProfile, 
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
    instance_name           = models.CharField(max_length=30)
    website                 = models.URLField(max_length=200, blank=True)
    
    url                     = models.CharField(unique=False, max_length=16, blank=False, 
                                               validators=[RegexValidator(regex="^[\w\-\.]*$")],
                                               help_text="Input an URL identifier for this course.")
    
    starting_time           = models.DateTimeField()
    ending_time             = models.DateTimeField()
    
    # Relations
    assistants              = models.ManyToManyField(UserProfile,
                                                     related_name=u"assisting_courses", 
                                                     blank=True)
    course                  = models.ForeignKey(Course, related_name=u"instances")
    
    plugins                 = generic.GenericRelation(BasePlugin, object_id_field="container_pk", content_type_field="container_type")
    
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
        return UserProfile.objects.filter(query)
    
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