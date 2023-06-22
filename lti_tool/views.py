import logging

from django.http import HttpResponse
from django.views.decorators.clickjacking import xframe_options_exempt
from django.views.decorators.csrf import csrf_exempt
from django.shortcuts import redirect, get_object_or_404
from django.contrib.auth.models import User
from django.contrib.auth import login
from django.urls import reverse
from django.utils.decorators import method_decorator
from pylti1p3.contrib.django import DjangoOIDCLogin, DjangoMessageLaunch
from pylti1p3.deep_link_resource import DeepLinkResource
from pylti1p3.lineitem import LineItem
from pylti1p3.exception import LtiException

from course.views import InstanceView, ModuleView
from course.models import CourseInstance, Enrollment, CourseModule
from course.viewbase import CourseInstanceBaseView, CourseModuleBaseView
from exercise.cache.points import ExerciseEntry
from exercise.viewbase import ExerciseBaseView
from exercise.models import LearningObject, BaseExercise
from exercise.views import ExerciseView, SubmissionView
from lib.localization_syntax import pick_localized
from lib.viewbase import BaseTemplateView, BaseRedirectView, BaseMixin
from authorization.permissions import ACCESS
from .utils import get_tool_conf, get_launch_data_storage, get_launch_url


logger = logging.getLogger('aplus.lti_tool')


@csrf_exempt
@xframe_options_exempt
def lti_login(request):
    tool_conf = get_tool_conf()
    launch_data_storage = get_launch_data_storage()

    oidc_login = DjangoOIDCLogin(request, tool_conf, launch_data_storage=launch_data_storage)
    target_link_uri = get_launch_url(request)
    return oidc_login.enable_check_cookies().redirect(target_link_uri)


@method_decorator(csrf_exempt, name='dispatch')
@method_decorator(xframe_options_exempt, name='dispatch')
class LtiLaunchView(BaseRedirectView):

    access_mode = ACCESS.ANONYMOUS

    def post(self, request, *args, **kwargs):
        tool_conf = get_tool_conf()
        launch_data_storage = get_launch_data_storage()
        message_launch = DjangoMessageLaunch(self.request, tool_conf, launch_data_storage=launch_data_storage)
        self.message_launch_data = message_launch.get_launch_data()

        # Get or create user
        try:
            # Moodle sends username in this parameter
            username = self.message_launch_data['https://purl.imsglobal.org/spec/lti/claim/ext']['user_username']
        except (KeyError, TypeError):
            # Email always received, use as fallback
            username = self.message_launch_data['email']
        try:
            self.user = User.objects.get(username=username)
        except User.DoesNotExist:
            self.user = User.objects.create_user(
                username,
                email=self.message_launch_data["email"],
                first_name=self.message_launch_data["given_name"],
                last_name=self.message_launch_data["family_name"],
            )
            profile = self.user.userprofile
            profile.language = (
                self.message_launch_data["https://purl.imsglobal.org/spec/lti/claim/launch_presentation"]["locale"]
            )
            profile.student_id = (
                self.message_launch_data["https://purl.imsglobal.org/spec/lti/claim/lis"]["person_sourcedid"]
            )
            # Note: profile.organization is not set since we can't know it
            # based on the LTI launch.
            profile.save()

        login(self.request, self.user, backend='django.contrib.auth.backends.ModelBackend')
        self.request.session["lti-launch-id"] = message_launch.get_launch_id()

        if message_launch.is_resource_launch():
            launch_params = self.message_launch_data["https://purl.imsglobal.org/spec/lti/claim/custom"]
            instance = get_object_or_404(CourseInstance,
                course__url=launch_params["course_slug"],
                url=launch_params["instance_slug"]
            )
            roles = self.message_launch_data["https://purl.imsglobal.org/spec/lti/claim/roles"]
            is_course_teacher = instance.is_course_staff(self.user)
            if "http://purl.imsglobal.org/vocab/lis/v2/membership#Learner" in roles and not is_course_teacher:
                instance.enroll_student(self.user)

            if "exercise_path" in launch_params:
                url_params = {
                    k: launch_params[k] for k in ["exercise_path", "module_slug", "course_slug", "instance_slug"]
                }
                return redirect("lti-exercise", **url_params)
            if "module_slug" in launch_params:
                url_params = {
                    k: launch_params[k] for k in ["module_slug", "course_slug", "instance_slug"]
                }
                return redirect("lti-module", **url_params)
            if "course_slug" in launch_params and "instance_slug" in launch_params:
                url_params = {
                    k: launch_params[k] for k in ["course_slug", "instance_slug"]
                }
                return redirect("lti-course", **url_params)
            raise LtiException("Invalid parameters for an LTI launch")
        if message_launch.is_deep_link_launch():
            return redirect("lti-select-content")
        raise LtiException("Invalid LTI launch type")


class LtiSessionMixin(BaseMixin):

    @method_decorator(xframe_options_exempt)
    def dispatch(self, request, *args, **kwargs):
        return super().dispatch(request, *args, **kwargs)

    def parse_lti_session_params(self):
        launch_id = self.request.session.get("lti-launch-id", None)
        tool_conf = get_tool_conf()
        if launch_id:
            self.message_launch = DjangoMessageLaunch.from_cache(
                launch_id,
                self.request,
                tool_conf,
                launch_data_storage=get_launch_data_storage()
            )
            self.message_launch_data = self.message_launch.get_launch_data()

    def get_common_objects(self):
        super().get_common_objects()
        self.disable_staff_nav = True
        self.submission_poll_ready_url_name = "lti-submission"
        self.note(
            "disable_staff_nav",
            "submission_poll_ready_url_name",
        )


class LtiInstanceView(LtiSessionMixin, InstanceView):

    access_mode = ACCESS.ENROLLED
    template_name = "lti_tool/lti_course.html"

    def get(self, request, *args, **kwargs):
        # Edit links to point to LTI views
        module_model_objs = CourseModule.objects.filter(course_instance=self.instance)
        learningobjects = LearningObject.objects.filter(course_module__course_instance=self.instance)
        for module in self.content.data.modules:
            module_model_obj = next((x for x in module_model_objs if x.id == module.id), None)
            module.update({'link': module_model_obj.get_url("lti-module")})
            for exercise in module.children:
                lo_model_obj = next((x for x in learningobjects if x.id == exercise.id), None)
                exercise.update({'link': lo_model_obj.get_url("lti-exercise")})
        return super().get(request, *args, **kwargs)


class LtiModuleView(LtiSessionMixin, ModuleView):

    access_mode = ACCESS.ENROLLED
    template_name = "lti_tool/lti_module.html"

    def get(self, request, *args, **kwargs):
        learningobjects = LearningObject.objects.filter(course_module=self.module)
        learningobjects_dict = { obj.id: obj for obj in learningobjects }
        # Can't use self.children for iteration, so this instead
        flat_module = self.content.flat_module(self.module, level_markers=False)
        exercises = [entry for entry in flat_module if isinstance(entry, ExerciseEntry)]
        for exercise in exercises:
            learningobj = learningobjects_dict[exercise.id]
            exercise.link = learningobj.get_url('lti-exercise')
        return super().get(request, *args, **kwargs)


class LtiExerciseView(LtiSessionMixin, ExerciseView):

    access_mode = ACCESS.ENROLLED
    template_name = "lti_tool/lti_exercise.html"
    post_url_name = "lti-exercise"
    submission_url_name = "lti-submission"
    exercise_url_name = "lti-exercise"

    # The dispatch method needs to be overridden here so that we can apply
    # different method decorators specifically in this class.
    # csrf_exempt is needed since it is used in ExerciseView and
    # the exercise forms do not include any csrf token.
    @method_decorator(csrf_exempt)
    @method_decorator(xframe_options_exempt)
    def dispatch(self, request, *args, **kwargs):
        return super().dispatch(request, *args, **kwargs)

    def post(self, request, *args, **kwargs):
        return super().post(request, *args, **kwargs, redirect_view='lti-submission')


class LtiSubmissionView(LtiSessionMixin, SubmissionView):

    access_mode = ACCESS.ENROLLED
    template_name = "lti_tool/lti_submission.html"
    submission_url_name = "lti-submission"
    exercise_url_name = 'lti-exercise'


class LtiSelectContentMixin(LtiSessionMixin):

    access_mode = ACCESS.TEACHER

    def get_resource_objects(self):
        super().get_resource_objects()
        try:
            # If the session (cookie) has been lost,
            # AnonymousUser does not have a user profile.
            user_profile = self.request.user.userprofile
        except AttributeError:
            self.is_teacher = False
        else:
            self.is_teacher = (
                self.request.user.is_superuser
                or Enrollment.objects.filter(
                    user_profile=user_profile,
                    role=Enrollment.ENROLLMENT_ROLE.TEACHER,
                    status=Enrollment.ENROLLMENT_STATUS.ACTIVE,
                ).exists()
            )

    def get_common_objects(self):
        super().get_common_objects()
        self.parse_lti_session_params()
        #FIXME do not include old, closed courses so that the course lists are reasonable
        if self.request.user.is_superuser:
            self.teaching_courses = CourseInstance.objects.all()
        else:
            self.teaching_courses = CourseInstance.objects.get_teaching(self.request.user.userprofile)


class LtiSelectContentView(LtiSelectContentMixin, BaseTemplateView):

    template_name = "lti_tool/course_list.html"

    def get_common_objects(self):
        super().get_common_objects()
        self.instances = self.teaching_courses
        self.note("instances")


class LtiSelectCourseView(LtiSelectContentMixin, CourseInstanceBaseView):

    template_name = "lti_tool/module_list.html"

    def post(self, request, *args, **kwargs):
        # Create gradebook items
        ags = self.message_launch.get_ags()
        lineitems = ags.get_lineitems()
        exercises = BaseExercise.objects.filter(course_module__course_instance=self.instance)
        for e in exercises:
            lineitem_exists = bool([li for li in lineitems if li['tag'] == str(e.id)])
            if e.max_points > 0 and not lineitem_exists:
                li = LineItem()
                li.set_tag(str(e.id)).set_score_maximum(e.max_points).set_label(pick_localized(str(e), 'en'))
                ags.find_or_create_lineitem(li)

        # Send activity settings
        deep_link = self.message_launch.get_deep_link()
        resource = DeepLinkResource()
        (resource.set_url(request.build_absolute_uri(reverse('lti-launch')))
            .set_custom_params({
                "course_slug": kwargs['course_slug'],
                "instance_slug": kwargs['instance_slug']
            })
            .set_title(
                "{}: {}".format(
                    pick_localized(self.course.name, 'en'),
                    pick_localized(self.instance.instance_name, 'en')
                )
            )
        )
        return HttpResponse(deep_link.output_response_form([resource]))

    # Get list of modules in course
    def get(self, request, *args, **kwargs):
        self.modules = list(self.instance.course_modules.all())
        self.note("modules")
        return super().get(request, *args, **kwargs)


class LtiSelectModuleView(LtiSelectContentMixin, CourseModuleBaseView):

    template_name = "lti_tool/exercise_list.html"

    def post(self, request, *args, **kwargs):
        # Create gradebook items
        ags = self.message_launch.get_ags()
        lineitems = ags.get_lineitems()
        exercises = BaseExercise.objects.filter(course_module=self.module)
        for e in exercises:
            lineitem_exists = bool([li for li in lineitems if li['tag'] == str(e.id)])
            if e.max_points > 0 and not lineitem_exists:
                li = LineItem()
                li.set_tag(str(e.id)).set_score_maximum(e.max_points).set_label(pick_localized(str(e), 'en'))
                ags.find_or_create_lineitem(li)

        # Send activity settings
        deep_link = self.message_launch.get_deep_link()
        resource = DeepLinkResource()
        (resource.set_url(request.build_absolute_uri(reverse('lti-launch')))
            .set_custom_params({
                "course_slug": kwargs['course_slug'],
                "instance_slug": kwargs['instance_slug'],
                "module_slug": kwargs['module_slug']
            })
            .set_title(pick_localized(str(self.module), 'en')))
        return HttpResponse(deep_link.output_response_form([resource]))

    # Get list of exercises in module
    def get(self, request, *args, **kwargs):
        self.learningobjects = LearningObject.objects.filter(course_module=self.module)
        self.learningobjects_dict = { obj.id: obj for obj in self.learningobjects }
        self.flat_module = list(self.content.flat_module(self.module))
        exercises = [entry for entry in self.flat_module if isinstance(entry, ExerciseEntry)]
        for exercise in exercises:
            learningobj = self.learningobjects_dict[exercise.id]
            exercise.link = learningobj.get_url('lti-select-exercise')
        self.note("learningobjects", "flat_module")
        return super().get(request, *args, **kwargs)


class LtiSelectExerciseView(LtiSelectContentMixin, ExerciseBaseView):

    def post(self, request, *args, **kwargs):
        # Create gradebook items
        ags = self.message_launch.get_ags()
        children = self.exercise.children.all()
        if len(children) > 0:
            for e in children:
                if e.max_points > 0:
                    li = LineItem()
                    li.set_tag(str(e.id)).set_score_maximum(e.max_points).set_label(pick_localized(str(e), 'en'))
                    ags.find_or_create_lineitem(li)
        else:
            try:
                if self.exercise.max_points > 0:
                    li = LineItem()
                    (li.set_tag(str(self.exercise.id))
                        .set_score_maximum(self.exercise.max_points)
                        .set_label(pick_localized(str(self.exercise), 'en')))
                    ags.find_or_create_lineitem(li)
            except AttributeError:
                logger.info("Importing LTI exercise with no max_points attribute")

        # Send activity settings
        deep_link = self.message_launch.get_deep_link()
        resource = DeepLinkResource()
        (resource.set_url(request.build_absolute_uri(reverse('lti-launch')))
            .set_custom_params({
                "course_slug": kwargs['course_slug'],
                "instance_slug": kwargs['instance_slug'],
                "module_slug": kwargs['module_slug'],
                "exercise_path": kwargs['exercise_path']
            })
            .set_title(pick_localized(str(self.exercise), 'en')))
        return HttpResponse(deep_link.output_response_form([resource]))
