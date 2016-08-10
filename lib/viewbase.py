"""
Defines base views for extending and mixing to higher level views.
The structure was created for handling nested models.
"""
from django.core.exceptions import PermissionDenied
from django.http.response import HttpResponseRedirect
from django.utils.http import is_safe_url
from django.views.generic.base import TemplateResponseMixin, TemplateView, View
from django.views.generic.edit import FormMixin, FormView

from lib.helpers import deprecated
from authorization.views import AuthorizedResourceMixin
from authorization.permissions import (
    Permission,
)


class AccessControlPermission(Permission):
    def has_permission(self, request, view):
        try:
            view.access_control()
            return True
        except PermissionDenied:
            return False


class BaseMixin(object):
    """
    Extend to handle data and mixin with one of the views implementing
    get/post methods. Calling the super method is required when overriding
    the base methods.
    """
    base_permission_classes = [
        AccessControlPermission,
    ]

    def get_permissions(self):
        perms = super().get_permissions()
        perms.extend((Perm() for Perm in self.base_permission_classes))
        return perms

    @deprecated("access_control is deprecated and should be replaced with correct permission_classes")
    def access_control(self):
        """
        Support old access_control system with AccessControlPermission
        """
        pass

    @deprecated("self.handle() is deprecated. There is no need to call it anymore.")
    def handle(self):
        pass

    def _get_kwarg(self, kw, **kwargs):
        arg = self.kwargs.get(kw)
        if not arg:
            if "default" in kwargs:
                return kwargs["default"]
            raise AttributeError(
                "Missing argument from URL pattern: {}".format(kw))
        return arg


class BaseViewMixin(AuthorizedResourceMixin):
    permission_classes = [] # common come from BaseMixin and this drops NoPermission default
    pass


class BaseView(BaseViewMixin, View):
    pass


class BaseTemplateMixin(BaseMixin, TemplateResponseMixin):
    template_name = None
    ajax_template_name = None
    force_ajax_template = False

    @deprecated("self.response() is deprecated and should be replaced with super().get(...)")
    def response(self, **kwargs):
        return self.render_to_response(self.get_context_data(**kwargs))

    def get_template_names(self):
        if self.force_ajax_template or self.request.is_ajax() or not self.template_name:
            if self.ajax_template_name:
                return [self.ajax_template_name]
        return super().get_template_names()


class BaseTemplateView(BaseTemplateMixin, BaseViewMixin, TemplateView):
    pass


class BaseRedirectMixin(BaseMixin):

    def redirect_kwarg(self, kw, backup=None):
        to = self.request.POST.get(kw, self.request.GET.get(kw, ""))
        return self.redirect(to, backup)

    def redirect(self, to, backup=None):
        if not is_safe_url(url=to, host=self.request.get_host()):
            if backup:
                to = backup.get_absolute_url()
            else:
                raise AttributeError(
                    "Redirect attempt to unsafe url: {}".format(to))
        return HttpResponseRedirect(to)


class BaseRedirectView(BaseRedirectMixin, BaseViewMixin, View):
    pass


class BaseFormMixin(BaseRedirectMixin, BaseTemplateMixin, FormMixin):
    def form_valid(self, form):
        return self.redirect(self.get_success_url())


class BaseFormView(BaseFormMixin, BaseViewMixin, FormView):
    pass


class PagerMixin(object):
    page_kw = "page"
    per_page = 10

    def get_common_objects(self):
        super().get_common_objects()
        self.page = self._parse_page(self.page_kw)
        self.note("page", "per_page")

    def _parse_page(self, parameter_name):
        try:
            value = self.request.GET.get(parameter_name)
            if value:
                return max(1, int(value))
        except ValueError:
            pass
        return 1
