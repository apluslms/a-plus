from django import template
from django.template.defaultfilters import stringfilter
from django.utils.safestring import mark_safe

register = template.Library()

# Cleaner(frames=False, forms=False, page_structure=False, embedded=False)

# import html5lib
# from html5lib import sanitizer

@register.filter
@stringfilter
def sanitize(value):
    #p = html5lib.HTMLParser(tokenizer=sanitizer.HTMLSanitizer)
    #sanitized = p.parseFragment(value).toxml()
    return mark_safe(value)
