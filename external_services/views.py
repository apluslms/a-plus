"""
Provides LTI access to external services with current course and user identity.
"""
import logging
from urllib.parse import urlsplit, parse_qsl, urlparse, parse_qs

from django.contrib import messages
from django.core.exceptions import PermissionDenied
from django.http import HttpResponse, JsonResponse, HttpRequest
from django.shortcuts import get_object_or_404
from django.utils.translation import gettext_lazy as _
from django.conf import settings
from django.views.decorators.clickjacking import xframe_options_exempt
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator

from oauthlib.common import Request as OAuthRequest
from oauthlib.openid.connect.core.endpoints.pre_configured import Server as OIDCServer
from oauthlib.oauth2.rfc6749.errors import OAuth2Error
from oauthlib.oauth2.rfc6749 import tokens
from jwcrypto import jwk
import json

from authorization.permissions import ACCESS
from course.viewbase import CourseInstanceBaseView, CourseInstanceMixin
from course.templatetags.course import parse_localization
from lib.helpers import build_aplus_url
from lib.viewbase import BaseFormView, BaseRedirectView, BaseView, BaseTemplateView
from .forms import MenuItemForm
from .lti import LTIRequest
from .lti1p3 import LTI1p3AuthValidator, LTI1p3TokenValidator, prepare_lti1p3_initiate_login
from .models import MenuItem, LTI1p3Service
from .permissions import MenuVisiblePermission, LTIServicePermission

logger = logging.getLogger('aplus.external_services')


class ExternalLinkView(CourseInstanceBaseView):
    template_name = "external_services/launch.html"
    id_kw = "menu_id"
    menu_permission_classes = (
        MenuVisiblePermission,
    )

    def get_permissions(self):
        perms = super().get_permissions()
        perms.extend((Perm() for Perm in self.menu_permission_classes))
        return perms

    def get_resource_objects(self):
        super().get_resource_objects()
        self.menu_item = get_object_or_404(
            MenuItem,
            pk=self._get_kwarg(self.id_kw),
            course_instance=self.instance
        )

    def get_common_objects(self):
        super().get_common_objects()
        self.service = service = self.menu_item.service # pylint: disable=unused-variable
        self.service_label = self.menu_item.label
        url = urlsplit(self.menu_item.final_url)
        self.url = url._replace(query='', fragment='').geturl()
        self.site = site = '/'.join(self.url.split('/')[:3])
        self.parameters = parse_qsl(url.query)
        self.parameters_hash = site
        self.note("service", "service_label", "parameters_hash", "parameters", "site", "url")


class LTILoginView(CourseInstanceBaseView):
    """
    Generates an LTI POST form for a service.
    Implements LTI 1.0 using required and most recommended parameters.
    Tested for use with Piazza, https://piazza.com/product/lti
    """
    access_mode = ACCESS.ENROLLED
    template_name = "external_services/launch.html"
    id_kw = "menu_id"
    menu_permission_classes = (
        MenuVisiblePermission,
        LTIServicePermission,
    )

    def get_permissions(self):
        perms = super().get_permissions()
        perms.extend((Perm() for Perm in self.menu_permission_classes))
        return perms

    def get_resource_objects(self):
        super().get_resource_objects()
        self.menu_item = get_object_or_404(
            MenuItem,
            pk=self._get_kwarg(self.id_kw),
            course_instance=self.instance
        )

    def get_common_objects(self):
        super().get_common_objects()
        self.service = self.menu_item.service
        self.service_label = self.menu_item.label
        self.url = self.menu_item.final_url
        self.site = '/'.join(self.url.split('/')[:3])

        try:
            if isinstance(self.service, LTI1p3Service):
                self.url = self.service.login_url
                self.parameters = prepare_lti1p3_initiate_login(self.service, self.request.user, self.instance)
            else:
                lti = LTIRequest(
                    self.service,
                    self.request.user,
                    self.instance,
                    self.request,
                    parse_localization(self.menu_item.label),
                )
                self.parameters_hash = lti.get_checksum_of_parameters(only_user_and_course_level_params=True)
                self.parameters = lti.sign_post_parameters(self.url)
                self.note("parameters_hash")
        except PermissionDenied:
            messages.error(self.request, _('EXTERNAL_SERVICE_MUST_BE_ENROLLED_TO_ACCESS_ANONYMOUS_SERVICE'))
            raise

        self.note("service", "service_label", "parameters", "site", "url")


@method_decorator(csrf_exempt, name='dispatch')
@method_decorator(xframe_options_exempt, name='dispatch')
class LTI1p3AuthRequestView(BaseTemplateView):
    """
    LTI 1.3 Authentication request from LTI Tool. This can be either a GET or POST
    message according to the OIDC specification.
    """
    access_mode = ACCESS.ANONYMOUS
    template_name = "external_services/authlogin.html"

    def get(self, request: HttpRequest, *args, **kwargs) -> HttpResponse:
        try:
            validator = LTI1p3AuthValidator(request.user, request.GET, request.GET.get('lti_message_hint'))
        except OAuth2Error as e:
            logger.error("Validating Authentication request failed: %s", e)
            return HttpResponse('Validating Authentication request failed', status=400)
        return self._process_auth_request(request=request, validator=validator, kwargs=kwargs)

    def post(self, request: HttpRequest, *args, **kwargs) -> HttpResponse:
        try:
            validator = LTI1p3AuthValidator(request.user, request.GET, request.POST.get('lti_message_hint'))
        except OAuth2Error as e:
            logger.error("Validating Authentication request failed: %s", e)
            return HttpResponse('Validating Authentication request failed', status=400)

        return self._process_auth_request(request=request, validator=validator, kwargs=kwargs)

    def _process_auth_request(
            self,
            request: HttpRequest,
            validator: LTI1p3AuthValidator,
            **kwargs,
    ) -> HttpResponse:

        server = OIDCServer(validator)
        oa_request = OAuthRequest(request.build_absolute_uri(), request.method, '', request.headers)
        scopes, credentials = server.validate_authorization_request(
            request.build_absolute_uri(),
            request.method,
            '',
            request.headers,
        )
        headers, _, _ = server.create_authorization_response(
            oa_request.uri,
            oa_request.http_method,
            scopes=scopes,
            credentials=credentials,
        )

        logger.info("LTI 1.3: OAuth2 login request from user: %d, client_id: %s",
                    request.user.pk,
                    credentials.get('client_id', 'None'))

        # Template creates an auto-submitted POST form from create_authorization_response output
        context = super().get_context_data(**kwargs)
        context['action'] = headers['Location']
        logger.info("LTI 1.3: Posting response to %s", headers['Location'])
        url = headers['Location'].replace("#", "?")
        params = parse_qs(urlparse(url).query)
        context['params'] = params

        return self.render_to_response(context)


class LTI1p3JwksView(BaseView):
    """
    JSON Web Key used by LTI tool to validate JSON web tokens sent in LTI messages.
    """
    access_mode = ACCESS.ANONYMOUS

    def get(self, request, *args, **kwargs) -> HttpResponse:
        pem = settings.APLUS_AUTH_LOCAL['PRIVATE_KEY']
        key = jwk.JWK.from_pem(pem.encode("utf8"))
        data = {"alg": "RS256", "use": "sig", "kid": key.thumbprint()}
        data.update(json.loads(key.export_public()))
        response = JsonResponse({"keys": [data]})
        return response


@method_decorator(csrf_exempt, name='dispatch')
class LTI1p3TokenView(BaseView):
    """
    Process incoming access token request for LTI 1.3.
    """
    access_mode = ACCESS.ANONYMOUS

    def post(self, request, *args, **kwargs):
        validator = LTI1p3TokenValidator()
        server = OIDCServer(
            validator,
            token_generator=tokens.signed_token_generator(
                settings.APLUS_AUTH_LOCAL['PRIVATE_KEY'],
                issuer=build_aplus_url(''),
            ),
            token_expires_in=settings.LTI_TOKEN_LIFETIME,
        )

        headers, body, status = server.create_token_response(
            request.build_absolute_uri(),
            request.method,
            request.body,
            request.headers,
            None,  # Additional credentials, maybe can omit entirely?
        )

        response = HttpResponse(content=body, headers=headers, status=status)
        return response


class ListMenuItemsView(CourseInstanceBaseView):
    access_mode = ACCESS.TEACHER
    template_name = "external_services/list_menu.html"

    def get_common_objects(self):
        super().get_common_objects()
        self.menu_items = self.instance.ext_services.prefetch_related('service')
        self.note("menu_items")


class EditMenuItemView(CourseInstanceMixin, BaseFormView):
    access_mode = ACCESS.TEACHER
    template_name = "external_services/edit_menu.html"
    form_class = MenuItemForm
    menu_item_kw = "menu_id"

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()

        menu_id = self._get_kwarg(self.menu_item_kw, default=None)
        if menu_id:
            self.menu_item = get_object_or_404(
                MenuItem,
                pk=menu_id,
                course_instance=self.instance
            )
            self.note("menu_item")
        else:
            self.menu_item = MenuItem(course_instance=self.instance)

        kwargs["instance"] = self.menu_item
        return kwargs

    def get_success_url(self):
        return self.instance.get_url("external-services-list-menu")

    def form_valid(self, form):
        form.save()
        return super().form_valid(form)


class RemoveMenuItemView(CourseInstanceMixin, BaseRedirectView):
    access_mode = ACCESS.TEACHER
    menu_item_kw = "menu_id"

    def get_resource_objects(self):
        super().get_resource_objects()
        self.menu_item = get_object_or_404(
            MenuItem,
            id=self._get_kwarg(self.menu_item_kw),
            course_instance=self.instance,
        )
        self.note("menu_item")

    def post(self, request, *args, **kwargs):
        self.menu_item.delete()
        return self.redirect(self.instance.get_url("external-services-list-menu"))
