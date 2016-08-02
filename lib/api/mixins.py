class ListSerializerMixin(object):
    # FIXME: use rest_framework_extensions.mixins.DetailSerializerMixin
    def get_serializer_class(self):
        if self.action == 'list':
            return getattr(self, 'listserializer_class', self.serializer_class)
        return super(ListSerializerMixin, self).get_serializer_class()


class MeUserMixin(object):
    me_user_url_kw = 'user_id'
    me_user_value = 'me'

    def dispatch(self, request, *args, **kwargs):
        kw = self.me_user_url_kw
        value = kwargs.get(kw, None)
        if value and self.me_user_value == value:
            kwargs[kw] = request.user.id
        return super(MeUserMixin, self).dispatch(request, *args, **kwargs)
