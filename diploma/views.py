from django.core.exceptions import PermissionDenied
from django.http import HttpResponse
from django.shortcuts import get_object_or_404
from django.views.generic.base import View

from exercise.cache.content import CachedContent
from exercise.cache.points import CachedPoints
from lib.viewbase import BaseRedirectView

from .grade import assign_grade
from .models import CourseDiplomaDesign, StudentDiploma
from .pdf import render_diploma


class CreateDiploma(BaseRedirectView):

    def post(self, request, *args, **kwargs):
        design = get_object_or_404(CourseDiplomaDesign, id=kwargs['coursediploma_id'])
        profile = get_object_or_404(UserProfile, id=kwargs['userprofile_id'])
        if (
            not request.user.is_authenticated()
            or not design.course
            or (
                profile.id != request.user.userprofile.id
                and not design.course.is_course_staff(request.user)
            )
        ):
            raise PermissionDenied()

        diploma = StudentDiploma.objects.filter(design=design, profile=profile).first()
        if not diploma:
            diploma = StudentDiploma(design=design, profile=profile)
            diploma.generate_hashkey()

        content = CachedContent(design.course)
        points = CachedPoints(design.course, profile.user, content)

        diploma.name = profile.user.get_full_name()
        diploma.grade = assign_grade(points, design)
        diploma.save()

        return self.redirect(diploma.get_absolute_url())


class ViewDiploma(View):

    def get(self, request, *args, **kwargs):
        diploma = get_object_or_404(StudentDiploma, hashkey=kwargs['diploma_hash'])
        response = HttpResponse(content_type='application/pdf')
        render_diploma(request, response, diploma)
        return response
