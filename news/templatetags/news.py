from django import template
from django.utils import timezone

from lib.errors import TagUsageError
from ..cache import CachedNews
from ..models import News


register = template.Library()


@register.inclusion_tag("news/user_news.html", takes_context=True)
def user_news(context, num, more=0):
    if not 'instance' in context:
        raise TagUsageError()
    if not 'now' in context:
        context['now'] = timezone.now()
    if not 'course_news' in context:
        context['course_news'] = CachedNews(context['instance'])
    news = context['course_news']

    if context['is_course_staff']:
        alerts,news = news.for_staff()
    else:
        user = context['request'].user
        alerts,news = news.for_user(
            not user.is_authenticated
            or user.userprofile.is_external
        )

    i = 0
    for item in news:
        i += 1
        item['collapsed'] = i > num
        if more > 0 and i == more:
            item['begin_more'] = True

    return {
        'is_course_staff': context['is_course_staff'],
        'now': context['now'],
        'alerts': alerts,
        'news': news,
        'more': more,
    }


@register.filter
def is_published(entry, now):
    return entry['publish'] <= now


@register.filter
def news_audience(audience):
    return News.AUDIENCE[audience]
