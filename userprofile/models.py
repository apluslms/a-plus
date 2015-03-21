# Django
from django.contrib.auth.models import User
from django.db import models
from django.db.models.signals import post_save
from django.db.models import Q


class UserProfile(models.Model):
    user        = models.OneToOneField(User)
    lang        = models.CharField(max_length=5, default="en_US")
    student_id  = models.CharField(max_length=25, null=True, blank=True)

    @classmethod
    def get_by_student_id(cls, student_id):
        return cls.objects.get(student_id=student_id)
    
    def __unicode__(self):
        return self.user.username
    
    def _generate_gravatar_url(self):
        import hashlib
        hash    = hashlib.md5(self.user.email).hexdigest()
        return "http://www.gravatar.com/avatar/" + hash +"?d=identicon"
    avatar_url = property(_generate_gravatar_url)

    def get_shortname(self):
        """
        Returns a short version of the user's name, with the first name and the first letter 
        of the last name.
        """
        try:
            return self.user.first_name + " " + self.user.last_name[0] + "."
        except:
            return self.user.username
    
    shortname = property(get_shortname)
    
    def get_courseinstance_staff_queryset(self):
        from course.models import CourseInstance
        return CourseInstance.objects.filter( Q(assistants__id=self.id) | Q(course__teachers__id=self.id) )

    def is_staff(self):
        return self.user.is_staff or self.user.is_superuser

    def get_unread_notification_count(self):
        return len(self.received_notifications.filter(seen=False))

    def get_unread_notification_course_instances(self):
        notifications = self.received_notifications.filter(seen=False)
        courses = set()
        for notification in notifications:
            courses.add(notification.course_instance)
        return courses
    
    class Meta:
        ordering            = ['id']

    # TODO: Remove this method and replace all usages with prefetch_related
    # when updating to newer Django version.
    def reset_hidden_categories_cache(self):
        self.cached_hidden_categories = self.hidden_categories.all()

    # TODO: Remove this method and replace all usages with prefetch_related
    # when updating to newer Django version.
    def get_hidden_categories_cache(self):
        self.cached_hidden_categories = getattr(self,
                                                "cached_hidden_categories",
                                                self.hidden_categories.all())
        return self.cached_hidden_categories


def create_user_profile(sender, instance, created, **kwargs):
    '''
    This function automatically creates an user profile for all new User models. The profiles 
    are used for extending the User models with domain specific attributes and behavior.
    
    @param sender: the signal(?) that invoked the function
    @param instance: the User object that was just created
    @param created: a boolean whether the object was created and not just updated
    '''
    if created:
        UserProfile.objects.get_or_create(user=instance)

post_save.connect(create_user_profile, sender=User)


class StudentGroup(models.Model):
    members         = models.ManyToManyField(UserProfile, related_name="groups")
    name            = models.CharField(max_length=32, unique=True)
    description     = models.CharField(max_length=256)
    member_limit    = models.PositiveIntegerField()
    is_public       = models.BooleanField(default=False)
    invitation_key  = models.CharField(max_length=10, blank=True)
    
    def get_names(self):
        return ", ".join(x.shortname for x in self.members.all())
    
    def has_space_left(self):
        return self.members.count() < self.member_limit
    
    def add_member(self, new_member):
        if self.members.count() >= self.member_limit:
            return False
        
        self.members.add(new_member)
        return True
    
    def __unicode__(self):
        return self.name
    
    class Meta:
        ordering            = ['name']
    
    @classmethod
    def get_students_from_request(cls, request):
        """
        Returns a QuerySet of students that belong to the group currently in session.
        If there is no group set, only the current user will be in the returned set.
        
        @param request: an HttpRequest object from Django
        @return: QuerySet of students that belong to the group currently in session
        """
        # Get the group of the student, if one is set in the request's META
        student_group       = request.META.get("STUDENT_GROUP", None)
        students            = None
        
        if student_group:
            students = student_group.members.all()
        else:
            # No group was found, so use just the current user
            students = UserProfile.objects.filter(id=request.user.userprofile.id)
        
        return students

