from django.db.models.signals import post_save, post_delete
from django.utils import timezone

from lib.cache import CachedAbstract
from .models import News


class CachedNews(CachedAbstract):
    KEY_PREFIX = 'news'

    def __init__(self, course_instance):
        self.instance = course_instance
        super().__init__(course_instance)

    def _generate_data(self, instance, data=None):
        alerts = []
        news = []
        for item in instance.news.all():
            entry = {
                'id': item.id,
                'audience': item.audience,
                'publish': item.publish,
                'title': item.title,
                'body': item.body,
                'pin': item.pin,
                'alert': item.alert,
            }
            if item.pin and item.alert:
                alerts.append(entry)
            else:
                news.append(entry)
        return {
            'alerts': alerts,
            'news': news,
        }

    def for_staff(self):
        return self.data['alerts'], self.data['news']

    def for_user(self, is_external=True):
        EXTERNAL = (News.AUDIENCE.EXTERNAL_USERS, News.AUDIENCE.ALL_USERS)
        INTERNAL = (News.AUDIENCE.INTERNAL_USERS, News.AUDIENCE.ALL_USERS)
        def filter_news(items, audiences):
            now = timezone.now()
            return [
                item for item in items if (
                    item['publish'] <= now
                    and item['audience'] in audiences
                )
            ]
        if is_external:
            return (
                filter_news(self.data['alerts'], EXTERNAL),
                filter_news(self.data['news'], EXTERNAL),
            )
        return (
            filter_news(self.data['alerts'], INTERNAL),
            filter_news(self.data['news'], INTERNAL),
        )

    @classmethod
    def is_visible(cls, entry, when=None):
        when = when or timezone.now()
        return entry['publish'] <= when


def invalidate_content(sender, instance, **kwargs):
    CachedNews.invalidate(instance.course_instance)


# Automatically invalidate cached news when edited.
post_save.connect(invalidate_content, sender=News)
post_delete.connect(invalidate_content, sender=News)
