# Tastypie
from tastypie.resources import ModelResource
from tastypie.authentication import Authentication, OAuthAuthentication
from tastypie.authorization import DjangoAuthorization, ReadOnlyAuthorization
from tastypie import fields

# A+
from course.models import Course, CourseInstance

class CourseResource(ModelResource):
    instances           = fields.ToManyField('course.api.CourseInstanceResource', 'instances')
    
    class Meta:
        queryset        = Course.objects.all()
        resource_name   = 'course'
        excludes        = []
        
        # TODO: In this version, only GET requests are accepted and no 
        # permissions are checked.
        allowed_methods = ['get']
        authentication  = Authentication()
        authorization   = ReadOnlyAuthorization()

class CourseInstanceResource(ModelResource):
    course_modules      = fields.ToManyField('exercise.api.CourseModuleResource', 'course_modules')
    
    def dehydrate(self, bundle):
        bundle.data.update({"is_open": bundle.obj.is_open()})
        bundle.data.update({"browser_url": bundle.obj.get_absolute_url()})
        return bundle
    
    class Meta:
        queryset        = CourseInstance.objects.all()
        resource_name   = 'courseinstance'
        excludes        = []
        
        # TODO: In this version, only GET requests are accepted and no 
        # permissions are checked.
        allowed_methods = ['get']
        authentication  = Authentication()
        authorization   = ReadOnlyAuthorization()