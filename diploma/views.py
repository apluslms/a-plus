from typing import Any

from django.core.exceptions import PermissionDenied
from django.http import HttpResponse, HttpRequest
from django.shortcuts import get_object_or_404
from django.views.generic.base import View

from authorization.permissions import ACCESS
from course.viewbase import CourseInstanceMixin
from exercise.cache.points import CachedPoints
from lib.helpers import settings_text
from lib.viewbase import BaseTemplateView, BaseRedirectView
from userprofile.models import UserProfile

from .grade import calculate_grade, assign_grade
from .models import CourseDiplomaDesign, StudentDiploma
from .pdf import render_diploma


class DiplomaMixin(CourseInstanceMixin):
    diploma_kw = 'coursediploma_id'
    userprofile_kw = 'userprofile_id'

    def get_course_instance_object(self):
        self.design = get_object_or_404(
            CourseDiplomaDesign,
            id=self.kwargs[self.diploma_kw],
        )
        return self.design.course

    def get_profile_object(self):
        return get_object_or_404(
            UserProfile,
            id=self.kwargs[self.userprofile_kw],
        )


class DiplomaListView(DiplomaMixin, BaseTemplateView):
    access_mode = ACCESS.ASSISTANT
    template_name = "diploma/list.html"

    def get_common_objects(self) -> None:
        super().get_common_objects()

        students = self.instance.students.all()
        group = self.request.GET.get("group")
        if group == "internal":
            students = [s for s in students if not s.is_external]
        elif group == "external":
            students = [s for s in students if s.is_external]

        point_limits = self.design.point_limits
        pad_points = self.design.pad_points
        student_grades = []
        for profile in students:
            points = CachedPoints(self.instance, profile.user, self.content, self.is_course_staff)
            student_grades.append((
                profile,
                calculate_grade(points.total(), point_limits, pad_points),
            ))
        self.student_grades = student_grades
        self.group = group
        self.internal_user_label = settings_text('INTERNAL_USER_LABEL')
        self.external_user_label = settings_text('EXTERNAL_USER_LABEL')
        self.note('student_grades', 'group', 'internal_user_label', 'external_user_label')


class DiplomaCreateView(DiplomaMixin, BaseRedirectView):
    access_mode = ACCESS.ENROLLED

    def post(self, request: HttpRequest, *args: Any, **kwargs: Any) -> HttpResponse:
        design = self.design
        profile = self.get_profile_object()
        if (profile != self.profile and not self.is_course_staff):
            raise PermissionDenied()

        points = CachedPoints(self.instance, profile.user, self.is_course_staff)
        grade = assign_grade(points, design)
        if grade < 0:
            raise PermissionDenied()

        diploma = StudentDiploma.objects.filter(design=design, profile=profile).first()
        if not diploma:
            diploma = StudentDiploma(design=design, profile=profile)
            diploma.generate_hashkey()

        diploma.name = profile.user.get_full_name()
        diploma.grade = grade
        diploma.save()

        return self.redirect(diploma.get_absolute_url())


class DiplomaPdfView(View):

    def get(self, request, *args, **kwargs):
        diploma = get_object_or_404(StudentDiploma, hashkey=kwargs['diploma_hash'])
        response = HttpResponse(content_type='application/pdf')
        render_diploma(request, response, diploma)
        return response
