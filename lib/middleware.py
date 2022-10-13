from django.conf import settings
from django.http import HttpResponseRedirect
from django.utils import translation
from django.utils.cache import patch_vary_headers
from django.utils.deprecation import MiddlewareMixin
from django.shortcuts import render

from lib.helpers import remove_query_param_from_url


class LocaleMiddleware(MiddlewareMixin):

    response_redirect_class = HttpResponseRedirect

    def process_request(self, request): # pylint: disable=inconsistent-return-statements
        query_language = request.GET.get('hl')
        if query_language:
            language = query_language
            lang_codes = set(lang[0][:2] for lang in settings.LANGUAGES)
            if language[:2] not in lang_codes:
                url = remove_query_param_from_url(request.get_full_path(), 'hl')
                return render(request, '404.html', {'url_without_language': url}, status=404)
        elif hasattr(request, 'user') and request.user.is_authenticated and not request.user.is_anonymous:
            language = request.user.userprofile.language
        else:
            language = translation.get_language_from_request(request)
        language = language[:2]
        translation.activate(language)
        request.LANGUAGE_CODE = translation.get_language()

    def process_response(self, request, response):
        language = translation.get_language()
        patch_vary_headers(response, ('Accept-Language',))
        if 'Content-Language' not in response:
            response['Content-Language'] = language
        return response
