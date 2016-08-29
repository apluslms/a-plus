from django.conf.urls import url
from tastypie import fields
from tastypie.authentication import Authentication
from tastypie.authorization import ReadOnlyAuthorization
from tastypie.bundle import Bundle
from tastypie.resources import ModelResource, Resource

from cached.content import CachedContent
from cached.points import CachedPoints
from userprofile.models import UserProfile

from ..models import Course, CourseInstance, CourseModule


class CourseResource(ModelResource):
    instances = fields.ToManyField('course.api.v1.CourseInstanceResource', 'instances')

    class Meta:
        queryset = Course.objects.all()
        resource_name = 'course'
        excludes = []

        # TODO: In this version, only GET requests are accepted and no
        # permissions are checked.
        allowed_methods = ['get']
        authentication = Authentication()
        authorization = ReadOnlyAuthorization()


class CourseInstanceResource(ModelResource):
    course_modules = fields.ToManyField('course.api.v1.CourseModuleResource', 'course_modules')

    def dehydrate(self, bundle):
        bundle.data.update({
            "is_open": bundle.obj.is_open(),
            "browser_url": bundle.obj.get_absolute_url()
        })
        # TODO add results_uri
        return bundle

    class Meta:
        # TODO: In this version, those course instances that have
        # visible_to_students == False are not accessible through the api.
        # However, they should be accessible through proper authorization.
        queryset = CourseInstance.objects.filter(
            visible_to_students=True)
        resource_name = 'courseinstance'
        excludes = []

        # TODO: In this version, only GET requests are accepted and no
        # permissions are checked.
        allowed_methods = ['get']
        authentication = Authentication()
        authorization = ReadOnlyAuthorization()


class CourseInstanceOverallSummaryResource(Resource):

    class Meta:
        object_class = object
        allowed_methods = ['get']

    def obj_get(self, request=None, **kwargs):
        # TODO  return  summary containing scores from all users and for each
        #       user URI to the user specific results
        pass


class CourseInstanceSummaryResource(Resource):

    class Meta:
        resource_name = 'course_result'
        object_class = CourseInstance
        allowed_methods = ['get']
        api_name = 'v1'

    # From: http://www.maykinmedia.nl/blog/2012/oct/2/nested-resources-tastypie/
    def prepend_urls(self):
        return [
            url(r'^(?P<resource_name>%s)/(?P<pk>\w[\w/-]*)/user/(?P<user>\w[\w/-]*)/$' %
                (self._meta.resource_name),
                self.wrap_view('dispatch_detail'),
                name='api_dispatch_detail'),
            url(r'^(?P<resource_name>%s)/(?P<pk>\w[\w/-]*)/$' %
                (self._meta.resource_name),
                self.wrap_view('dispatch_overall'),
                name='api_dispatch_list'),
            url(r'^(?P<resource_name>%s)/$' %
                (self._meta.resource_name),
                self.wrap_view('dispatch_course_instances'),
                name='api_course_instances')
        ]


    def dispatch_overall(self, request, **kwargs):
        return CourseInstanceSummaryResource().dispatch('list', request, **kwargs)

    def dispatch_course_instances(self, request, **kwargs):
        return CourseInstanceResource().dispatch('list', request, **kwargs)

    def obj_get_list(self, request=None, **kwargs):
        # TODO
        return []

    def obj_get(self, request=None, **kwargs):
        results = {}
        course_instance = CourseInstance.objects.get(pk=kwargs["pk"])
        user_profile = UserProfile.objects.get(pk=kwargs["user"])
        points = CachedPoints(
            course_instance, user_profile.user,
            CachedContent(course_instance))
        results["user"] = user_profile.id
        results["course_instance"] = kwargs["pk"]

        grouped = {}
        for entry in points.exercises():
            m = entry['module_id']
            if not m in grouped:
                grouped[m] = []
            grouped[m].append({
                'exercise_id': entry['id'],
                'submission_count': entry['submission_count'],
                'completed_percentage': self._percentage(
                    entry['points'], entry['max_points']),
            })

        summary = []
        for entry in points.modules():
            summary.append({
                'exercise_round_id': entry['id'],
                'completed_percentage': self._percentage(
                    entry['points'], entry['max_points']),
                'closing_time': entry['closing_time'],
                'exercise_summaries': grouped[entry['id']],
            })

        results["summary"] = summary
        return results

    def _percentage(self, points, max_points):
        if max_points > 0:
            return int(round(100.0 * points / max_points))
        return 100

    def dehydrate(self, bundle):
        bundle.data.update(bundle.obj)
        return bundle


class CourseModuleResource(ModelResource):
    learning_objects = fields.ToManyField('exercise.api.v1.LearningObjectResource', 'learning_objects')

    class Meta:
        queryset = CourseModule.objects.all()
        resource_name = 'coursemodule'
        excludes = []

        # In the first version GET (read only) requests are
        # allowed and no authentication is required
        allowed_methods = ['get']
        authentication = Authentication()
        authorization = ReadOnlyAuthorization()
