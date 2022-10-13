from django.http import Http404, HttpResponse

from course.viewbase import CourseInstanceMixin
from lib.viewbase import BaseRedirectView
from .models import Notification


class NotificationRedirectView(CourseInstanceMixin, BaseRedirectView):
    notification_kw = "notification_id"

    def get_resource_objects(self):
        super().get_resource_objects()
        nid = self._get_kwarg(self.notification_kw)
        self.notification = Notification.objects.filter(
            id=nid,
            course_instance=self.instance,
        ).select_related("submission__exercise").first()
        if not self.notification:
            raise Http404()

    def get(self, request, *args, **kwargs):
        self.notification.seen = True
        self.notification.save()
        if self.notification.submission:
            return self.redirect(
                self.notification.submission.get_url('submission-plain')
            )
        return HttpResponse(
            "[Old Notification] {}: {}".format(
                self.notification.subject,
                self.notification.notification,
            )
        )
