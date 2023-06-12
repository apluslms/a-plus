"""
Defines base views for extending and mixing to higher level views.
The structure was created for handling nested models.
"""
from typing import Any, Callable, Dict, Optional

from django.http.response import HttpResponseRedirect
from django.utils.http import url_has_allowed_host_and_scheme
from django.views.generic.base import TemplateResponseMixin, TemplateView, View
from django.views.generic.edit import FormMixin, FormView

from authorization.views import AuthorizedResourceMixin
from authorization.permissions import AccessModePermission
from lib.helpers import is_ajax


class BaseMixin:
    """
    Extend to handle data and mixin with one of the views implementing
    get/post methods. Calling the super method is required when overriding
    the base methods.
    """
    # NOTE: access_mode is not defined here, so if any derived class forgets to
    # define it AccessModePermission will raise assertion error
    #access_mode = ACCESS.ANONYMOUS
    base_permission_classes = [
        AccessModePermission,
    ]

    def get_permissions(self):
        perms = super().get_permissions()
        perms.extend((Perm() for Perm in self.base_permission_classes))
        return perms

    def get_access_mode(self):
        return self.access_mode

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


class BaseView(BaseViewMixin, View):
    pass


class BaseTemplateMixin(BaseMixin, TemplateResponseMixin):
    template_name = None
    ajax_template_name = None
    force_ajax_template = False

    def get_template_names(self):
        if self.force_ajax_template or is_ajax(self.request) or not self.template_name:
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
        if not url_has_allowed_host_and_scheme(url=to, allowed_hosts={self.request.get_host()}):
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
    def get_initial_get_param_spec(self) -> Dict[str, Optional[Callable[[str], Any]]]:
        """Return (Field name -> converter callable) -dict that will be used to
        populate the initial values from the GET parameters.

        E.g. {"instance": int} will set the initial value of field "instance" to
        int(request.GET["instance"]). Set the converter to None if no conversion
        is needed.
        """
        return {}

    def get_initial(self) -> Dict[str, Any]:
        initial = super().get_initial()

        for name, converter in self.get_initial_get_param_spec().items():
            if name not in self.request.GET:
                continue

            value = self.request.GET[name]
            if converter is not None:
                try:
                    value = converter(value)
                except: # pylint: disable=bare-except
                    pass
            initial[name] = value

        return initial
