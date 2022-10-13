from django.contrib.contenttypes.models import ContentType
from django.db import models

from model_utils.managers import InheritanceManager


class ModelWithInheritanceManager(InheritanceManager):
    def get_queryset(self):
        return super().get_queryset().select_related('content_type').select_subclasses()


class ModelWithInheritance(models.Model):
    """
    BaseExercise is the base class for all exercise types.
    It contains fields that are shared among all types.
    """

    objects                 = ModelWithInheritanceManager()

    content_type            = models.ForeignKey(ContentType,
                                                on_delete=models.CASCADE,
                                                editable=False,
                                                null=True)

    class Meta:
        abstract = False

    def save(self, *args, **kwargs):
        """
        Overrides the default save method from Django. If the method is called for
        a new model, its content type will be saved in the database as well. This way
        it is possible to later determine if the model is an instance of the
        class itself or some of its subclasses.
        """

        if not self.content_type:
            self.content_type = ContentType.objects.get_for_model(self.__class__)

        super().save(*args, **kwargs)

    def as_leaf_class(self):
        """
        Checks if the object is an instance of a certain class or one of its subclasses.
        If the instance belongs to a subclass, it will be returned as an instance of
        that class.
        """

        content_type = self.content_type
        model_class = content_type.model_class()
        if (model_class == self.__class__):
            return self
        return model_class.objects.get(id=self.id)
