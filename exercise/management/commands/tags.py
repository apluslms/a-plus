from django.core.management.base import BaseCommand, CommandError

from course.cache.students import invalidate_students
from course.models import CourseInstance, UserTag, UserTagging
from userprofile.models import UserProfile


class Command(BaseCommand):
    help = 'Operates on student tags.'

    def add_arguments(self, parser):
        parser.add_argument('course_instance_id', help='Course instance id')
        parser.add_argument('set', choices=['set', 'setone'],
            help='Use "set" for setting tags to users based on a user-tag mapping file OR '
                 '"setone" to set the same tag to all users in the user list file.')
        parser.add_argument('tag_id', nargs='?', default=None,
            help='With "setone", this defines the id of the tag.')
        parser.add_argument('filename',
            help='File path to the user-tag mapping file with "set" '
                 '(file format: "user_id tag_id" per line) OR '
                 'user list file with "setone" (file format: one user id per line)')

    def handle(self, *args, **options):
        instance = CourseInstance.objects.filter(id=options['course_instance_id']).first()
        if not instance:
            raise CommandError('Course instance not found.')
        if options['set'] == 'set':
            if options.get('tag_id') is not None:
                raise CommandError('You may not use the tag id argument with "set"!')
            tag_ids = self.set_tags(instance, options['filename'])
            one_tag_id = tag_ids.pop()
        else:
            # setone command
            if options.get('tag_id') is None:
                raise CommandError('You must supply the tag id argument with "setone"!')
            self.set_tagone(instance, options['tag_id'], options['filename'])
            one_tag_id = options['tag_id']

        # Clear the student cache so that the course participants page shows updated tags.
        one_tag = UserTag.objects.filter(id=one_tag_id, course_instance=instance).first()
        invalidate_students(UserTag, one_tag)

    def set_tags(self, instance, filename):
        tag_ids = set()
        for tid,users in self.read_user_tag(filename).items():
            self.tag_users(instance, tid, users)
            tag_ids.add(tid)
        return tag_ids

    def set_tagone(self, instance, tid, filename):
        self.tag_users(instance, tid, self.read_user(filename))

    def tag_users(self, instance, tid, users):
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
        with open(filename, "r", encoding="utf-8") as f:
            for line in f:
                words = line.split()
                if len(words) == 2:
                    user,tag = words
                    if tag not in tag_map:
                        tag_map[tag] = []
                    tag_map[tag].append(user)
                elif len(words) != 0:
                    raise CommandError('Invalid line in user_id tag_id file: ' + line)
        return tag_map

    def read_user(self, filename):
        users = []
        with open(filename, "r", encoding="utf-8") as f:
            for line in f:
                words = line.split()
                if len(words) == 1:
                    users.append(words[0])
                elif len(words) != 0:
                    raise CommandError('Invalid line in user_id file: ' + line)
        return users
