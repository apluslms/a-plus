from typing import Any, Optional, TYPE_CHECKING

from aplus_auth.payload import Permission, Permissions
from django.conf import settings
from django.contrib.auth.models import User, AnonymousUser
from django.urls import reverse
from django.db import models
from django.db.models.signals import post_save
from django.utils.functional import cached_property
from django.utils.translation import gettext_lazy as _
from rest_framework.authtoken.models import Token

from authorization.object_permissions import ObjectPermissions

if TYPE_CHECKING:
    from django.db.models.manager import RelatedManager

    from course.models import CourseInstance
    from exercise.models import BaseExercise, Submission, SubmissionDraft
    from external_services.models import LTIService


class UserProfileQuerySet(models.QuerySet['UserProfile']):
    def prefetch_tags(self, instance: 'CourseInstance', to_attr: str = 'instance_taggings') -> 'UserProfileQuerySet':
        return self.prefetch_related(
            models.Prefetch(
                'taggings',
                instance.taggings.select_related('tag'),
                to_attr,
            ),
        )


class UserProfileManager(models.Manager):
    _queryset_class = UserProfileQuerySet

    def get_queryset(self):
        return super().get_queryset().select_related("user")

    def prefetch_tags(self, instance: 'CourseInstance', to_attr: str = 'instance_taggings') -> UserProfileQuerySet:
        return self.all().prefetch_tags(instance, to_attr)


class UserProfile(models.Model):
    """
    Additional user information and methods.
    """

    @classmethod
    def get_by_student_id(cls, student_id, org=settings.LOCAL_ORGANIZATION):
        # Because student ID is unique only within organization,
        # also organization needs to be specified.
        return cls.objects.get(student_id=student_id, organization=org)

    @classmethod
    def get_by_email(cls, email):
        return User.objects.filter(email=email).first().userprofile

    @classmethod
    def get_by_request(cls, request):
        user = request.user
        if user.is_authenticated:
            return user.userprofile
        raise RuntimeError("Seeking user profile without authenticated user.")

    user = models.OneToOneField(User,
        verbose_name=_('LABEL_USER'),
        on_delete=models.CASCADE,
    )
    language = models.CharField(
        verbose_name=_('LABEL_LANGUAGE'),
        max_length=5,
        blank=True,
        default='',
    )
    student_id = models.CharField(
        verbose_name=_('LABEL_STUDENT_ID'),
        max_length=25,
        blank=True, null=True,
    )
    organization = models.CharField(
        verbose_name=_('LABEL_ORGANIZATION'),
        max_length=80,
        blank=True,
    )
    objects = UserProfileManager()

    if TYPE_CHECKING:
        id: models.AutoField
        submissions: RelatedManager['Submission']
        graded_submissions: RelatedManager['Submission']
        submission_drafts: RelatedManager['SubmissionDraft']

    class Meta:
        verbose_name = _('MODEL_NAME_USER_PROFILE')
        verbose_name_plural = _('MODEL_NAME_USER_PROFILE_PLURAL')
        ordering = ['id']

    def __str__(self):
        if self.student_id == None:
            return f"{self.user.username} ({self.user.first_name} {self.user.last_name}, {self.user.email})"
        else:
            return f"{self.user.username} ({self.user.first_name} {self.user.last_name}, {self.user.email}, {self.student_id})"

    @cached_property
    def api_token(self):
        # FIXME: implement support for more than 1 token
        token, created = Token.objects.get_or_create(user=self.user)
        return token.key

    @cached_property
    def avatar_url(self):
        """
        URL address for gravatar image based on the user email.
        """
        import hashlib
        hash_key = hashlib.md5(self.user.email.encode('utf-8')).hexdigest()
        return "http://www.gravatar.com/avatar/" + hash_key + "?d=identicon"

    @cached_property
    def shortname(self):
        """
        A short version of the user's name in form "John D."
        """
        try:
            return self.user.first_name + " " + self.user.last_name[0] + "."
        except:
            return self.user.username

    @cached_property
    def name_with_student_id(self):
        name = self.user.get_full_name()
        if self.student_id:
            return name + ', ' + self.student_id
        return name

    @cached_property
    def is_external(self):
        """
        Is this an external rather than internal account.
        """
        return (self.organization != settings.LOCAL_ORGANIZATION)

    def get_url(self, instance):
        kwargs = dict(user_id=self.user.id, **instance.get_url_kwargs())
        return reverse('user-results', kwargs=kwargs)


def create_user_profile(sender, instance, created, **kwargs):
    """
    This function automatically creates an user profile for all new User models. The profiles
    are used for extending the User models with domain specific attributes and behavior.

    @param sender: the signal that invoked the function
    @param instance: the User object that was just created
    @param created: a boolean whether the object was created and not just updated
    """
    if created:
        UserProfile.objects.get_or_create(user=instance)

# Attach to the post_save signal.
post_save.connect(create_user_profile, sender=User)


class GraderUser(AnonymousUser):
    def __init__(self, username: str, permissions: ObjectPermissions, **extra: Any):
        self.username = username
        self.permissions = permissions
        self._extra = extra

    @property
    def is_anonymous(self):
        """GraderUser is anonymous, but not AnonymousUser"""
        return True

    @property
    def is_authenticated(self):
        return True

    # A-plus interface
    @property
    def userprofile(self):
        """Compatibilty with User.userprofile"""
        return self


class LTIServiceUser(GraderUser):
    def __init__(self, submission: "Submission" = None,
            exercise: "BaseExercise" = None,
            lti_service: Optional["LTIService"] = None,
            user_id: int = None,
            **kwargs: Any,
            ) -> None:
        """exercise and student_id must both be present if one is"""
        self.lti_service = lti_service
        permissions = ObjectPermissions()
        if submission:
            permissions.submissions.add(Permission.WRITE, submission)
        if exercise:
            if user_id:
                permissions.submissions.add_create(exercise=exercise, user_id=user_id)
            else:
                permissions.submissions.add_create(exercise=exercise)
        super().__init__("LTI", permissions, **kwargs)
