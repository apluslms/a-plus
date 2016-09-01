from django.db.models.signals import post_save, post_delete
from django.utils import timezone

from news.models import News
from .abstract import CachedAbstract


class CachedNews(CachedAbstract):
    KEY_PREFIX = 'news'

    def __init__(self, course_instance):
        self.instance = course_instance
        super().__init__(course_instance)

    def _generate_data(self, instance):
        entries = []
        for news in instance.news.all():
            entries.append({
                'id': news.id,
                'audience': news.audience,
                'publish': news.publish,
                'title': news.title,
                'body': news.body,
                'pin': news.pin,
                'alert': news.alert,
            })
        return {
            'news': entries,
        }

    def for_staff(self):
        return self.data['news']

    def for_user(self, is_external=True):
        def filter_news(audiences):
            now = timezone.now()
            return [
                item for item in self.data['news'] if (
                    item['publish'] <= now
                    and item['audience'] in audiences
                )
            ]
        if is_external:
            return filter_news((
                News.AUDIENCE.EXTERNAL_USERS,
                News.AUDIENCE.ALL_USERS,
            ))
        return filter_news((
            News.AUDIENCE.INTERNAL_USERS,
            News.AUDIENCE.ALL_USERS,
        ))

    @classmethod
    def is_visible(cls, entry, when=None):
        when = when or timezone.now()
        return entry['publish'] <= when


def invalidate_content(sender, instance, **kwargs):
    CachedNews.invalidate(instance.course_instance)


# Automatically invalidate cached news when edited.
post_save.connect(invalidate_content, sender=News)
post_delete.connect(invalidate_content, sender=News)
