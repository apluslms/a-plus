from django.core.management.base import BaseCommand, CommandError

from course.models import CourseInstance, UserTag, UserTagging
from userprofile.models import UserProfile


class Command(BaseCommand):
    args = 'course_id [set|setone tag_id] filename'
    help = 'Operates on student tags. File format has "user_id tag_id" per line.'

    def handle(self, *args, **options):
        if len(args) < 1:
            raise CommandError('Missing arguments: ' + self.args)
        instance = CourseInstance.objects.filter(id=args[0]).first()
        if not instance:
            raise CommandError('Course instance not found.')
        if args[1] == 'set':
            if len(args) != 3:
                raise CommandError('Missing arguments: ' + self.args)
            self.set_tags(instance, args[2])
        elif args[1] == "setone":
            if len(args) != 4:
                raise CommandError('Missing arguments: ' + self.args)
            self.set_tags(instance, args[2], args[3])
        else:
            raise CommandError('Unknown argument!')

    def set_tags(self, instance, filename):
        for tid,users in self.read_user_tag(filename).items():
            self.tag_users(instance, tid, users)

    def set_tagone(self, instance, tid, filename):
        self.tag_users(instance, tid, self.read_user(filename))

    def tag_users(instance, tid, users):
        tag = UserTag.objects.filter(id=tid, course_instance=instance).first()
        if not tag:
            raise CommandError('Tag was not found in this course: ' + tid)
        for uid in users:
            profile = UserProfile.objects.filter(user_id=uid).first()
            if not profile:
                raise CommandError('User was not found: ' + uid)
            if not instance.is_student(profile.user):
                raise CommandError('User is not student in this course: ' + uid)
            UserTagging.objects.set(profile, tag)

    def read_user_tag(self, filename):
        tag_map = {}
        with open(filename, "r") as f:
            for line in f:
                words = line.split()
                if len(words) == 2:
                    user,tag = words
                    if not tag in tag_map:
                        tag_map[tag] = []
                    tag_map[tag].append(user)
                elif len(words) != 0:
                    raise CommandError('Invalid line in user_id tag_id file: ' + line)
        return tag_map

    def read_user(self, filename):
        users = []
        with open(filename, "r") as f:
            for line in f:
                words = line.split()
                if len(words) == 1:
                    users.append(words[0])
                elif len(words) != 0:
                    raise CommandError('Invalid line in user_id file: ' + line)
        return users
