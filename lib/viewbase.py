"""
Defines base views for extending and mixing to higher level views.
The structure was created for handling nested models.
"""
from django.http.response import HttpResponseRedirect
from django.utils.http import is_safe_url
from django.views.generic.base import TemplateResponseMixin, ContextMixin, View
from django.views.generic.edit import FormMixin


class BaseMixin(object):
    """
    Extend to handle data and mixin with one of the views implementing
    get/post methods. Calling the super method is required when overriding
    the base methods.
    """
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._attr = []

    def get_resource_objects(self):
        """
        Get the resource objects sufficient to determine the existance.
        Should raise Http404 if the request does not reach a resource.
        Use self.note to announce attributes of further interest.
        """
        pass

    def access_control(self):
        """
        Access control the resource. Should raise PermissionDenied if
        access is not granted.
        """
        pass

    def get_common_objects(self):
        """
        Once access is verified further objects may be created that
        are common for different HTTP methods, e.g. get and post.
        Use self.note to announce attributes of further interest.
        """
        pass

    def note(self, *args):
        """
        The class attribute names given in argument list are marked
        "interesting" for the view. In a TemplateView these will be
        injected to the template context.
        """
        self._attr.extend(args)

    def handle(self):
        self.get_resource_objects()
        self.access_control()
        self.get_common_objects()

    def _get_kwarg(self, kw, **kwargs):
        arg = self.kwargs.get(kw)
        if not arg:
            if "default" in kwargs:
                return kwargs["default"]
            raise AttributeError(
                "Missing argument from URL pattern: {}".format(kw))
        return arg


class BaseTemplateMixin(TemplateResponseMixin):
    template_name = None
    ajax_template_name = None
    force_ajax_template = False

    def get(self, request, *args, **kwargs):
        self.handle()
        return self.response()

    def response(self, **kwargs):
        return self.render_to_response(self.get_context_data(**kwargs))

    def get_context_data(self, **kwargs):
        context = {"request": self.request}
        for key in self._attr:
            context[key] = getattr(self, key)
        context.update(kwargs)
        return context

    def get_template_names(self):
        if self.force_ajax_template or self.request.is_ajax() or not self.template_name:
            if self.ajax_template_name:
                return [self.ajax_template_name]
        return super().get_template_names()


class BaseTemplateView(BaseTemplateMixin, View):
    pass


class BaseRedirectMixin(object):

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


class BaseRedirectView(BaseRedirectMixin, View):
    pass


class BaseFormMixin(BaseRedirectMixin, BaseTemplateMixin, FormMixin):
    form_class = None
    success_url = None

    def get(self, request, *args, **kwargs):
        self.handle()
        form = self.get_form(self.get_form_class())
        return self.response(form=form)

    def post(self, request, *args, **kwargs):
        self.handle()
        form = self.get_form(self.get_form_class())
        if form.is_valid():
            return self.form_valid(form)
        return self.form_invalid(form)

    def form_valid(self, form):
        return self.redirect(self.get_success_url())

    def form_invalid(self, form):
        return self.response(form=form)


class BaseFormView(BaseFormMixin, View):
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
