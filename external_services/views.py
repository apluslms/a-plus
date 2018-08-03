"""
Provides LTI access to external services with current course and user identity.
"""
from django.contrib import messages
from django.core.exceptions import PermissionDenied
from django.http import Http404
from django.shortcuts import get_object_or_404
from django.utils.translation import ugettext_lazy as _

from authorization.permissions import ACCESS
from course.viewbase import CourseInstanceBaseView, CourseInstanceMixin
from lib.viewbase import BaseFormView, BaseRedirectView
from .forms import MenuItemForm
from .lti import LTIRequest
from .models import MenuItem
from .permissions import MenuVisiblePermission, LTIServicePermission

class LTILoginView(CourseInstanceBaseView):
    """
    Generates an LTI POST form for a service.
    Implements LTI 1.0 using required and most recommended parameters.
    Tested for use with Piazza, https://piazza.com/product/lti
    """
    access_mode = ACCESS.ENROLLED
    template_name = "external_services/lti_service_launch.html"
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
        self.service = self.menu_item.service.as_leaf_class()
        try:
            lti = LTIRequest(
                self.service,
                self.request.user,
                self.instance,
                self.request,
                self.menu_item.label,
            )
        except PermissionDenied:
            messages.error(self.request, _('You need to be enrolled to access an anonymous service.'))
            raise
        self.url = self.service.url
        self.parameters_hash = lti.get_checksum_of_parameters(only_user_and_course_level_params=True)
        self.parameters = lti.sign_post_parameters(self.url)
        self.site = '/'.join(self.url.split('/')[:3])
        self.note("service", "parameters_hash", "parameters", "site", "url")


class ListMenuItemsView(CourseInstanceBaseView):
    access_mode = ACCESS.TEACHER
    template_name = "external_services/list_menu.html"

    def get_common_objects(self):
        super().get_common_objects()
        self.menu_items = self.instance.ext_services.all()
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
