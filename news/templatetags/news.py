from django import template
from django.utils import timezone

from cached.news import CachedNews
from lib.errors import TagUsageError
from ..models import News


register = template.Library()


@register.inclusion_tag("news/user_news.html", takes_context=True)
def user_news(context, num):
    if not 'instance' in context:
        raise TagUsageError()
    if not 'now' in context:
        context['now'] = timezone.now()
    if not 'course_news' in context:
        context['course_news'] = CachedNews(context['instance'])
    news = context['course_news']

    if context['is_course_staff']:
        items = news.for_staff()
    else:
        user = context['request'].user
        items = news.for_user(
            not user.is_authenticated()
            or user.userprofile.is_external
        )

    i = 0
    for item in items:
        if item['pin'] and item['alert']:
            item['open'] = True
        else:
            item['open'] = i < num
            i += 1

    return {
        'is_course_staff': context['is_course_staff'],
        'now': context['now'],
        'news': items,
    }


@register.filter
def is_published(entry, now):
    return entry['publish'] <= now


@register.filter
def news_audience(audience):
    return News.AUDIENCE[audience]
