class ListSerializerMixin:
    # FIXME: use rest_framework_extensions.mixins.DetailSerializerMixin
    def get_serializer_class(self):
        if self.action == 'list':
            return getattr(self, 'listserializer_class', self.serializer_class)
        return super().get_serializer_class()


class MeUserMixin:
    me_user_url_kw = 'user_id'
    me_user_value = 'me'

    # Hook into `initial` method call chain.
    # after calling `initial` we have done all authentication related tasks,
    # so there is valid request.user also with token authentication
    # NOTE: self.kwargs is a pointer to the dict inside rest_framework / self.dispatch
    # and kwargs given to the initial is a copy of that dictionary.

    def initial(self, request, *args, **kwargs):
        super().initial(request, *args, **kwargs)

        kw = self.me_user_url_kw
        value = self.kwargs.get(kw, None)
        if value and self.me_user_value == value:
            self.kwargs[kw] = request.user.id if request.user.is_authenticated else None
