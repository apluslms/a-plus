class ListSerializerMixin(object):
    def get_serializer_class(self):
        if self.action == 'list':
            return getattr(self, 'listserializer_class', self.serializer_class)
        return super(ListSerializerMixin, self).get_serializer_class()
