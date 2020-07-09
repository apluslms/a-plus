from django.conf import settings
from django.http import HttpResponseRedirect
from django.utils import translation
from django.utils.cache import patch_vary_headers
from django.utils.deprecation import MiddlewareMixin


class LocaleMiddleware(MiddlewareMixin):

    response_redirect_class = HttpResponseRedirect

    def process_request(self, request):
        if hasattr(request, 'user') and request.user.is_authenticated:
            language = request.user.userprofile.language
        else:
            language = translation.get_language_from_request(request)
        translation.activate(language)
        request.LANGUAGE_CODE = translation.get_language()

    def process_response(self, request, response):
        language = translation.get_language()
        patch_vary_headers(response, ('Accept-Language',))
        if 'Content-Language' not in response:
            response['Content-Language'] = language
        return response
