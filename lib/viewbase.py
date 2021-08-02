"""
Defines base views for extending and mixing to higher level views.
The structure was created for handling nested models.
"""
from django.http.response import HttpResponseRedirect
from django.utils.http import is_safe_url
from django.views.generic.base import TemplateResponseMixin, TemplateView, View
from django.views.generic.edit import FormMixin, FormView

from authorization.views import AuthorizationMixin, AuthorizedResourceMixin
from authorization.permissions import AccessModePermission


class BaseMixin(AuthorizationMixin):
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
    pass


class BaseView(BaseViewMixin, View):
    pass


class BaseTemplateMixin(TemplateResponseMixin, BaseMixin):
    template_name = None
    ajax_template_name = None
    force_ajax_template = False

    def get_template_names(self):
        if self.force_ajax_template or self.request.is_ajax() or not self.template_name:
            if self.ajax_template_name:
                return [self.ajax_template_name]
        return super().get_template_names()


class BaseTemplateView(BaseViewMixin, BaseTemplateMixin, TemplateView):
    pass


class BaseRedirectMixin(BaseMixin):

    def redirect_kwarg(self, kw, backup=None):
        to = self.request.POST.get(kw, self.request.GET.get(kw, ""))
        return self.redirect(to, backup)

    def redirect(self, to, backup=None):
        if not is_safe_url(url=to, allowed_hosts={self.request.get_host()}):
            if backup:
                to = backup.get_absolute_url()
            else:
                raise AttributeError(
                    "Redirect attempt to unsafe url: {}".format(to))
        return HttpResponseRedirect(to)


class BaseRedirectView(BaseViewMixin, BaseRedirectMixin, View):
    pass


class BaseFormMixin(BaseTemplateMixin, FormMixin, BaseRedirectMixin):
    def form_valid(self, form):
        return self.redirect(self.get_success_url())


class BaseFormView(BaseFormMixin, BaseViewMixin, FormView):
    pass
