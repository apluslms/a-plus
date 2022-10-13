from functools import partial
from urllib.parse import urlencode

from django.db.models import Manager
from rest_framework import serializers
from rest_framework.serializers import HyperlinkedModelSerializer
from rest_framework.utils.field_mapping import get_nested_relation_kwargs
from rest_framework.fields import get_attribute

from .fields import NestedHyperlinkedIdentityField, NestedHyperlinkedRelatedField


class NestedHyperlinkedModelSerializer(HyperlinkedModelSerializer):
    """
    Extension of `HyperlinkedModelSerializer` that adds support for
    nested resources.
    """
    serializer_related_field = NestedHyperlinkedRelatedField
    serializer_url_field = NestedHyperlinkedIdentityField

    def get_default_field_names(self, declared_fields, model_info):
        """
        Return the default list of field names that will be used if the
        `Meta.fields` option is not specified.
        """
        return (
            [self.url_field_name] +
            list(declared_fields.keys()) +
            list(model_info.fields.keys()) +
            list(model_info.forward_relations.keys())
        )

    def build_nested_field(self, field_name, relation_info, nested_depth):
        """
        Create nested fields for forward and reverse relationships.
        """
        class NestedSerializer(NestedHyperlinkedModelSerializer):
            class Meta:
                model = relation_info.related_model
                depth = nested_depth - 1

        field_class = NestedSerializer
        field_kwargs = get_nested_relation_kwargs(relation_info)

        return field_class, field_kwargs


class AlwaysListSerializer:
    def __new__(cls, *args, **kwargs):
        if kwargs.pop('_many', True):
            kwargs['many'] = True
        return super(AlwaysListSerializer, cls).__new__(cls, *args, _many=False, **kwargs)

    def __init__(self, *args, _many=False, **kwargs):
        super().__init__(*args, **kwargs)


class HtmlViewField(serializers.ReadOnlyField):
    def __init__(self, *args, **kwargs):
        kwargs['source'] = '*'
        super().__init__(*args, **kwargs)

    def to_representation(self, obj): # pylint: disable=arguments-renamed
        request = self.context['request']
        url = obj.get_absolute_url()
        return request.build_absolute_uri(url)


class NestedHyperlinkedIdentityFieldWithQuery(NestedHyperlinkedIdentityField):
    def __init__(self, *args, query_params=None, **kwargs):
        self.__query_params = query_params
        super().__init__(*args, **kwargs)

    def get_url(self, obj, view_name, request, format): # pylint: disable=redefined-builtin
        url = super().get_url(obj, view_name, request, format)

        if url and self.__query_params:
            # pylint: disable-next=unnecessary-lambda-assignment
            get = lambda x: x(obj) if callable(x) else get_attribute(obj, x.split('.'))
            params = [(key, get(value)) for key, value in self.__query_params.items()]
            url = url + '?' + urlencode(params)

        return url


class AttributeProxy:
    def __init__(self, obj, **kwargs):
        self._obj = obj
        self._kwargs = kwargs

    def __getattr__(self, key):
        try:
            return self._kwargs[key]
        except KeyError:
            return getattr(self._obj, key)


def zip_instance_extra_with_iterable(instance, iterable, extra):
    extra_attrs = dict(
        (key, get_attribute(instance, attrs.split('.')))
        for key, attrs in extra.items()
    )
    return (AttributeProxy(item, **extra_attrs) for item in iterable)


class CompositeListSerializer(serializers.ListSerializer):
    @classmethod
    def with_extra(cls, extra):
        return partial(cls, extra=extra)

    def __init__(self, instance=None, data=serializers.empty, extra=None, **kwargs):
        self.__extra = extra
        source = kwargs.get('source', None)
        if instance and source:
            iterable = instance[source]
            instance = zip_instance_extra_with_iterable(instance, iterable, extra)
        super().__init__(instance=instance, data=data, **kwargs)

    def get_attribute(self, instance):
        data = super().get_attribute(instance)
        iterable = data.all() if isinstance(data, Manager) else data
        return zip_instance_extra_with_iterable(instance, iterable, self.__extra)


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


class StatisticsSerializer(serializers.Serializer):
    starttime = serializers.DateTimeField(allow_null=True)
    endtime = serializers.DateTimeField(allow_null=True)
    submission_count = serializers.IntegerField(read_only=True)
    submitters = serializers.IntegerField(read_only=True)
