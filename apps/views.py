from django.http.response import Http404
from django.shortcuts import get_object_or_404

from course.models import CourseInstance
from course.viewbase import CourseInstanceBaseView
from .models import BaseTab

class TabView(CourseInstanceBaseView):
    template_name = "plugins/view_tab.html"
    tab_kw = "tab_id"

    def get_resource_objects(self):
        super().get_resource_objects()
        self.tab_object = get_object_or_404(
            BaseTab,
            id=self._get_kwarg(self.tab_kw),
        )
        self.container = self.tab_object.container

        if isinstance(self.container, CourseInstance):
            if self.container.id != self.instance.id:
                raise Http404()
        else:
            raise TypeError("Unexptected tab container: {}".format(
                self.container.__class__))
        self.note('container')

    def get(self, request, *args, **kwargs):
        tab_renderer = self.tab_object.get_renderer_class()(
           self.tab_object,
           self.profile,
           self.container
        )
        return super().get(request, *args, **kwargs, tab=tab_renderer)

