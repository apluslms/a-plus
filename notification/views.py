from course.viewbase import CourseInstanceBaseView
from lib.viewbase import PagerMixin
from userprofile.viewbase import ACCESS

from .models import NotificationSet


class NotificationsView(PagerMixin, CourseInstanceBaseView):
    template_name = "notification/notifications.html"
    ajax_template_name = "notification/_notifications_list.html"

    def get_resource_objects(self):
        super().get_resource_objects()

        # Always require logged in student
        self.access_mode = ACCESS.STUDENT

    def get_common_objects(self):
        super().get_common_objects()
        notifications_set = NotificationSet.get_course(
            self.instance, self.request.user, self.per_page, self.page)
        self.count = notifications_set.count_and_mark_unseen()
        self.notifications = notifications_set.notifications
        self.note("count", "notifications", "per_page")
