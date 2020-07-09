from django.conf import settings
from django.contrib.auth.models import User, AnonymousUser
from django.urls import reverse
from django.db import models
from django.db.models.signals import post_save
from django.utils.functional import cached_property
from rest_framework.authtoken.models import Token


class UserProfileManager(models.Manager):

    def get_queryset(self):
        return super().get_queryset().select_related("user")


class UserProfile(models.Model):
    """
    Additional user information and methods.
    """

    @classmethod
    def get_by_student_id(cls, student_id):
        return cls.objects.get(student_id=student_id)

    @classmethod
    def get_by_email(cls, email):
        return User.objects.filter(email=email).first().userprofile

    @classmethod
    def get_by_request(cls, request):
        user = request.user
        if user.is_authenticated:
            return user.userprofile
        raise RuntimeError("Seeking user profile without authenticated user.")

    user = models.OneToOneField(User, on_delete=models.CASCADE)
    language = models.CharField(max_length=5, blank=True, default='')
    student_id = models.CharField(max_length=25, null=True, blank=True)
    objects = UserProfileManager()

    class Meta:
        ordering = ['id']

    def __str__(self):
        if self.student_id == None:
            return "{} ({} {})".format(self.user.username, self.user.first_name, self.user.last_name)
        else:
            return "{} ({} {}, {})".format(self.user.username, self.user.first_name, self.user.last_name, self.student_id)

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
        return not bool(self.student_id)

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
    @classmethod
    def from_submission(cls, submission):
        return cls(submission=submission)

    @classmethod
    def from_exercise(cls, exercise, student_id):
        return cls(exercise=exercise, student_id=student_id)

    def __init__(self, submission=None, exercise=None, **extra):
        self._submission = submission
        if exercise:
            self._exercise = exercise
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

    @cached_property
    def _exercise(self):
        return self._submission.exercise

    @cached_property
    def _course_instance(self):
        return self._exercise.course_module.course_instance

    @cached_property
    def _course(self):
        return self._course_instance.course


class LTIServiceUser(GraderUser):
    def __init__(self, submission=None, exercise=None, lti_service=None, **kwargs):
        self.lti_service = lti_service
        super().__init__(submission=submission, exercise=exercise, **kwargs)
