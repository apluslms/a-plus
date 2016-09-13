from django.http import Http404, HttpResponse

from authorization.permissions import ACCESS
from course.viewbase import CourseInstanceBaseView, CourseInstanceMixin
from lib.viewbase import PagerMixin, BaseRedirectView
from .models import NotificationSet, Notification


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
                self.notification.submission.exercise.get_display_url()
            )
        return HttpResponse(
            "[Old Notification] {}: {}".format(
                self.notification.subject,
                self.notification.notification,
            )
        )


class NotificationsView(PagerMixin, CourseInstanceBaseView):
    """
    Deprecated: not used anymore,
    single place for message in submission feedback
    """
    access_mode = ACCESS.ENROLLED
    template_name = "notification/notifications.html"
    ajax_template_name = "notification/_notifications_list.html"

    def get_access_mode(self):
        access_mode = super().get_access_mode()

        # Always require at least logged in student
        if access_mode < ACCESS.STUDENT:
            access_mode = ACCESS.STUDENT

        return access_mode

    def get_common_objects(self):
        super().get_common_objects()
        notifications_set = NotificationSet.get_course(
            self.instance, self.request.user, self.per_page, self.page)
        self.count = notifications_set.count_and_mark_unseen()
        self.notifications = notifications_set.notifications
        self.note("count", "notifications", "per_page")
