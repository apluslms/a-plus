from rest_framework.serializers import HyperlinkedModelSerializer
 
class NamespacedHyperlinkedModelSerializer(HyperlinkedModelSerializer):
    def build_relational_field(self, *args, **kwargs):
        field_class, field_kwargs = \
            super(NamespacedHyperlinkedModelSerializer, self).build_relational_field(*args, **kwargs)

        if 'view_name' in field_kwargs:
            field_kwargs['view_name'] = 'api:' + field_kwargs['view_name']

        return field_class, field_kwargs