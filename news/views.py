from django.core.exceptions import PermissionDenied
from django.http import Http404
from django.shortcuts import get_object_or_404

from authorization.permissions import ACCESS
from course.viewbase import CourseInstanceBaseView, CourseInstanceMixin
from lib.viewbase import BaseFormView, BaseRedirectView
from .forms import NewsForm
from .models import News


class ListNewsView(CourseInstanceBaseView):
    access_mode = ACCESS.TEACHER
    template_name = "news/list.html"

    def get_common_objects(self):
        super().get_common_objects()
        self.news = self.instance.news.all()
        self.note("news")


class EditNewsView(CourseInstanceMixin, BaseFormView):
    access_mode = ACCESS.TEACHER
    template_name = "news/edit.html"
    form_class = NewsForm
    news_item_kw = "news_id"

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()

        news_id = self._get_kwarg(self.news_item_kw, default=None)
        if news_id:
            self.news_item = get_object_or_404(
                News,
                pk=news_id,
                course_instance=self.instance
            )
            self.note("news_item")
        else:
            self.news_item = News(course_instance=self.instance)

        kwargs["instance"] = self.news_item
        return kwargs

    def get_success_url(self):
        return self.instance.get_url("news-list")

    def form_valid(self, form):
        form.save()
        return super().form_valid(form)


class RemoveNewsView(CourseInstanceMixin, BaseRedirectView):
    access_mode = ACCESS.TEACHER
    news_item_kw = "news_id"

    def get_resource_objects(self):
        super().get_resource_objects()
        self.news_item = get_object_or_404(
            News,
            id=self._get_kwarg(self.news_item_kw),
            course_instance=self.instance,
        )
        self.note("news_item")

    def post(self, request, *args, **kwargs):
        self.news_item.delete()
        return self.redirect(self.instance.get_url("news-list"))
