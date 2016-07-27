from rest_framework import serializers


class HtmlViewField(serializers.ReadOnlyField):
    def __init__(self, *args, **kwargs):
        super(HtmlViewField, self).__init__(*args, **kwargs)

    def get_attribute(self, obj):
        return obj

    def to_representation(self, obj):
        request = self.context['request']
        url = obj.get_absolute_url()
        return request.build_absolute_uri(url)
