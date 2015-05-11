# Django
from django.conf.urls import url
from django.core.urlresolvers import reverse
from django.contrib.auth.models import User

# Tastypie
from tastypie.resources import ModelResource, Resource
from tastypie.authentication import Authentication #, OAuthAuthentication
from tastypie.authorization import DjangoAuthorization, ReadOnlyAuthorization
from tastypie import fields
from tastypie.bundle import Bundle

# A+
from course.models import Course, CourseInstance
from exercise.exercise_summary import UserCourseSummary
from userprofile.models import UserProfile

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
        # TODO add results_uri
        return bundle

    class Meta:
        # TODO: In this version, those course instances that have
        # visible_to_students == False are not accessible through the api.
        # However, they should be accessible through proper authorization.
        queryset        = CourseInstance.objects.filter(
            visible_to_students=True)
        resource_name   = 'courseinstance'
        excludes        = []

        # TODO: In this version, only GET requests are accepted and no
        # permissions are checked.
        allowed_methods = ['get']
        authentication  = Authentication()
        authorization   = ReadOnlyAuthorization()

class CourseInstanceOverallSummaryResource(Resource):

    class Meta:
        object_class    = object
        allowed_methods = ['get']

    def obj_get(self, request=None, **kwargs):
        # TODO  return  summary containing scores from all users and for each
        #       user URI to the user specific results
        pass


class CourseInstanceSummaryResource(Resource):

    class Meta:
        resource_name   = 'course_result'
        object_class    = UserCourseSummary
        allowed_methods = ['get']
        api_name        = 'v1'

    #From: http://www.maykinmedia.nl/blog/2012/oct/2/nested-resources-tastypie/
    def override_urls(self):
        # TODO override_urls will be deprecated in Tastypie 1.0
        # http://django-tastypie.readthedocs.org/en/latest/api.html#override-urls
        return [
            url(r'^(?P<resource_name>%s)/(?P<pk>\w[\w/-]*)/user/(?P<user>\w[\w/-]*)/$' %
                (self._meta.resource_name ),
                self.wrap_view('dispatch_detail'),
                name='api_dispatch_detail'),
            url(r'^(?P<resource_name>%s)/(?P<pk>\w[\w/-]*)/$' %
                (self._meta.resource_name ),
                self.wrap_view('dispatch_overall'),
                name='api_dispatch_list'),
            url(r'^(?P<resource_name>%s)/$' %
                (self._meta.resource_name),
                self.wrap_view('dispatch_course_instances'),
                name='api_course_instances')
        ]

    def get_resource_uri(self, bundle_or_obj):
        kwargs = {
            'resource_name': self._meta.resource_name,
            'api_name': self._meta.api_name,
        }

        if isinstance(bundle_or_obj, Bundle):
            kwargs['user'] = bundle_or_obj.obj['user']
            kwargs['pk'] = bundle_or_obj.obj['course_instance']
        else:
            print(bundle_or_obj)
            kwargs['user'] = bundle_or_obj['user']
            kwargs['pk'] = bundle_or_obj['course_instance']

        return self._build_reverse_url("api_dispatch_detail", kwargs=kwargs)

    def dispatch_overall(self, request, **kwargs):
        return CourseInstanceSummaryResource().dispatch('list', request, **kwargs)

    def dispatch_course_instances(self, request, **kwargs):
        return CourseInstanceResource().dispatch('list', request, **kwargs)

    def obj_get_list(self, request=None, **kwargs):
        #TODO
        return []

    def obj_get(self, request=None, **kwargs):
        results         = {}
        course_instance = CourseInstance.objects.get(pk=kwargs["pk"])
        user_profile    = UserProfile.objects.get(pk=kwargs["user"])
        course_summary  = UserCourseSummary(course_instance, user_profile.user)
        results["user"] = user_profile.id
        results["course_instance"] = kwargs["pk"]
        summary = []

        for rnd in course_summary.round_summaries:
            exercise_summaries = []
            for ex_summary in rnd.exercise_summaries:
                tmp = {}
                tmp["exercise_id"] = ex_summary.exercise.id
                tmp["submission_count"] = ex_summary.submission_count
                tmp["completed_percentage"] = ex_summary.get_completed_percentage()
                exercise_summaries.append(tmp)
            summary.append({"exercise_round_id": rnd.exercise_round.id,
                              "completed_percentage": rnd.get_completed_percentage(),
                              "closing_time": rnd.exercise_round.closing_time,
                              "exercise_summaries": exercise_summaries
                            })
        results["summary"] = summary
        return results

    def dehydrate(self, bundle):
        bundle.data.update(bundle.obj)
        return bundle
