from django.db.models.signals import post_save, post_delete

from lib.cache import CachedAbstract
from .models import Notification


class CachedNotifications(CachedAbstract):
    KEY_PREFIX = "notifications"

    def __init__(self, user):
        super().__init__(user)

    def _generate_data(self, user, data=None): # pylint: disable=arguments-differ
        if not user or not user.is_authenticated:
            return {
                'count': 0,
                'notifications': [],
            }

        def notification_entry(n):
            exercise = n.submission.exercise if n.submission else None
            return {
                'id': n.id,
                'submission_id': n.submission.id if n.submission else 0,
                'name': "{} {}, {}".format(
                    n.course_instance.course.code,
                    (str(exercise.parent)
                        if exercise and exercise.parent else
                     n.course_instance.instance_name),
                    (str(exercise)
                        if exercise else
                     n.subject),
                ),
                'link': n.get_display_url(),
            }

        notifications = list(
            user.userprofile.received_notifications\
                .filter(seen=False)\
                .select_related(
                    'submission',
                    'submission__exercise',
                    'course_instance',
                    'course_instance__course',
                )
        )
        return {
            'count': len(notifications),
            'notifications': [notification_entry(n) for n in notifications],
        }

    def count(self):
        return self.data['count']

    def notifications(self):
        return self.data['notifications']


def invalidate_notifications(sender, instance, **kwargs): # pylint: disable=unused-argument
    CachedNotifications.invalidate(instance.recipient.user)


# Automatically invalidate cache when notifications change.
post_save.connect(invalidate_notifications, sender=Notification)
post_delete.connect(invalidate_notifications, sender=Notification)
