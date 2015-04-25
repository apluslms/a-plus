from django.db import models
from django.core.urlresolvers import reverse
from course.models import CourseInstance
from inheritance.models import ModelWithInheritance


class LinkService(ModelWithInheritance):
    '''
    Configures an external link class which works as a base class for LTIService
    '''
    url = models.CharField(
        max_length=256,
        help_text="The service URL"
    )
    menu_label = models.CharField(
        max_length=32,
        help_text="A default label to show in the course menu."
    )
    menu_icon_class = models.CharField(
        max_length=32,
        default="icon-globe",
        help_text="A default menu icon style name, see http://getbootstrap.com/components/#glyphicons-glyphs"
    )
    enabled = models.BooleanField(
        default=True,
        help_text="If not enabled, the service is disabled for all course instances."
    )

    class Meta:
        ordering = ["menu_label"]

    def __unicode__(self):
        out = "%s: %s" % (self.menu_label, self.url)
        if not self.enabled:
            return "[Disabled] " + out
        return out


class LTIService(LinkService):
    '''
    Configures an external LTI service. Extends LinkService.
    
    '''
    consumer_key = models.CharField(
        max_length=128,
        help_text="The consumer key provided by the LTI service."
    )
    consumer_secret = models.CharField(
        max_length=128,
        help_text="The consumer secret provided by the LTI service."
    )


class MenuItem(models.Model):
    '''
    Attaches LTI service to course instance menu.
    
    '''
    service = models.ForeignKey(LinkService)

    course_instance = models.ForeignKey(
        CourseInstance,
        related_name="ext_services",
        help_text="A course instance where the service is used."
    )
    menu_label = models.CharField(
        max_length=32,
        null=True,
        blank=True,
        help_text="Overrides service default label shown in the course menu."
    )
    menu_icon_class = models.CharField(
        max_length=32,
        null=True,
        blank=True,
        help_text="Overrides service default menu icon style, e.g. icon-star see http://getbootstrap.com/components/#glyphicons-glyphs"
    )
    menu_weight = models.IntegerField(
        default=0,
        help_text="Heavier menu entries are placed after lighter ones."
    )
    enabled = models.BooleanField(default=True)
    
    class Meta:
        ordering = ["course_instance", "menu_weight", "menu_label"]

    @property
    def label(self):
        '''
        @rtype: C{str}
        @return: menu label locally overwritten or from the service
        '''
        if self.menu_label:
            return self.menu_label
        return self.service.menu_label

    @property
    def icon_class(self):
        '''
        @rtype: C{str}
        @return: menu icon class locally overwritten or from the service
        '''
        if self.menu_icon_class:
            return self.menu_icon_class
        return self.service.menu_icon_class

    @property
    def url(self):
        '''
        @rtype: C{str}
        @return: menu url
        '''
        if type(self.service.as_leaf_class()) == LTIService:
            return reverse('external_services.views.lti_login', args=[self.id])
        return self.service.url

    def __unicode__(self):
        out = "%s %s: " % (self.course_instance.course.code, self.course_instance.instance_name)
        if not self.enabled or not self.service.enabled:
            return "[Disabled] " + out
        return out
