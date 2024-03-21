from collections import defaultdict

from django import template
from django.utils import timezone

from lib.errors import TagUsageError
from ..cache import CachedNews
from ..models import News
from django.utils.translation import get_language

register = template.Library()


@register.inclusion_tag("news/user_news.html", takes_context=True)
def user_news(context, num, more=0): # pylint: disable=unused-argument
    if 'instance' not in context:
        raise TagUsageError()
    if 'now' not in context:
        context['now'] = timezone.now()
    if 'course_news' not in context:
        context['course_news'] = CachedNews(context['instance'])
    news = context['course_news']

    if context['is_course_staff']:
        news = news.for_staff()
    else:
        user = context['request'].user
        news = news.for_user(
            not user.is_authenticated
            or user.userprofile.is_external
        )

    language_to_news = defaultdict(list)
    for item in news:
        language_to_news[item['language']].append(item)

    # Get news of current chosen language AND news items with All language
    language_dict = language_to_news['-'] + language_to_news[get_language()]

    return {
        'is_course_staff': context['is_course_staff'],
        'now': context['now'],
        'news': news,
        'language_news': language_dict,
        'instance_language': get_language(),
        'more': more,
    }


@register.filter
def is_published(entry, now):
    return entry['publish'] <= now


@register.filter
def news_audience(audience):
    return News.AUDIENCE[audience]
