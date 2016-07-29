from rest_framework import serializers
from rest_framework_extensions.fields import NestedHyperlinkedIdentityField
from rest_framework_extensions.serializers import NestedHyperlinkedModelSerializer


class AlwaysListSerializer(object):
    def __new__(cls, *args, **kwargs):
        if kwargs.pop('_many', True):
            kwargs['many'] = True
        return super(AlwaysListSerializer, cls).__new__(cls, *args, _many=False, **kwargs)

    def __init__(self, *args, _many=False, **kwargs):
        super(AlwaysListSerializer, self).__init__(*args, **kwargs)


class HtmlViewField(serializers.ReadOnlyField):
    def __init__(self, *args, **kwargs):
        kwargs['source'] = '*'
        super(HtmlViewField, self).__init__(*args, **kwargs)

    def to_representation(self, obj):
        request = self.context['request']
        url = obj.get_absolute_url()
        return request.build_absolute_uri(url)


class AplusSerializerMetaMetaclass(type):
    def __new__(cls, name, bases, dict_):
        new_cls = type.__new__(cls, name, bases, dict_)
        for k, v in dict_.items():
            if k[0] != '_' and not callable(v):
                if isinstance(v, dict):
                    parent = getattr(super(new_cls, new_cls), k, {})
                    setattr(new_cls, k, dict(parent, **v))
                elif isinstance(v, (tuple, list)):
                    parent = getattr(super(new_cls, new_cls), k, ())
                    seen = set()
                    seen_add = seen.add
                    res = [x for x in parent if not (x in seen or seen_add(x))]
                    res += (x for x in v if not (x in seen or seen_add(x)))
                    setattr(new_cls, k, type(v)(res))
        return new_cls


class AplusSerializerMeta(metaclass=AplusSerializerMetaMetaclass):
    pass


class AplusModelSerializerBase(NestedHyperlinkedModelSerializer):
    url_field_name = 'url'
    html_url_field_name = 'html_url'

    def get_field_names(self, declared_fields, info):
        fields = list(super().get_field_names(declared_fields, info))
        extra_kwargs = getattr(self.Meta, 'extra_kwargs', {})
        if self.url_field_name not in fields and self.url_field_name in extra_kwargs:
            fields.insert(0, self.url_field_name)
        return fields

    def build_unknown_field(self, field_name, model_class):
        if field_name == self.html_url_field_name:
            return (HtmlViewField, {})
        if field_name == self.url_field_name:
            extra_kwargs = getattr(self.Meta, 'extra_kwargs', {})
            kwargs = {'context': self.context}
            kwargs.update(extra_kwargs[self.url_field_name])
            return (NestedHyperlinkedIdentityField, kwargs)
        return super().build_unknown_field(field_name, model_class)


class AplusModelSerializer(AplusModelSerializerBase):
    id = serializers.IntegerField(source='pk', read_only=True)

    class Meta(AplusSerializerMeta):
        fields = (
            'id',
            'url',
        )
