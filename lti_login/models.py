from django.db import models
from course.models import CourseInstance


class LTIService(models.Model):
    '''
    Configures an external LTI service.
    
    '''
    lti_url = models.CharField(max_length=256,
        help_text="The LTI service URL")
    consumer_key = models.CharField(max_length=128,
        help_text="The consumer key provided by the LTI service.")
    consumer_secret = models.CharField(max_length=128,
        help_text="The consumer secret provided by the LTI service.")

    enabled = models.BooleanField(default=True)

    menu_label = models.CharField(max_length=32,
        help_text="A default label to show in the course menu.")
    menu_icon_class = models.CharField(max_length=32, default="icon-comment",
        help_text="A default menu icon style name, see http://getbootstrap.com/components/#glyphicons-glyphs")

    class Meta:
        ordering = ["menu_label"]

    def __unicode__(self):
        out = u"%s: %s" % (self.menu_label, self.lti_url)
        if not self.enabled:
            return u"[Disabled] " + out
        return out


class LTIMenuItem(models.Model):
    '''
    Attaches LTI service to course instance menu.
    
    '''
    service = models.ForeignKey(LTIService, related_name="menu_items")
    course_instance = models.ForeignKey(CourseInstance, related_name="lti_services",
        help_text="A course instance where the service is used.")
    menu_label = models.CharField(max_length=32, null=True, blank=True,
        help_text="Overrides service default label shown in the course menu.")
    menu_icon_class = models.CharField(max_length=32, null=True, blank=True,
        help_text="Overrides service default menu icon style, e.g. icon-star see http://getbootstrap.com/components/#glyphicons-glyphs")
    menu_weight = models.IntegerField(default=0,
        help_text="Heavier menu entries are placed after lighter ones.")
    enabled = models.BooleanField(default=True)
    
    class Meta:
        ordering = ["course_instance", "menu_weight", "menu_label"]

    def __unicode__(self):
        out = u"%s %s: " % (self.course_instance.course.code, self.course_instance.instance_name)
        if self.menu_label:
            out += self.menu_label
        else:
            out += self.service.menu_label
        if not self.enabled or not self.service.enabled:
            return u"[Disabled] " + out
        return out
