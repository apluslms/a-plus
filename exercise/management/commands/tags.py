from django.core.management.base import BaseCommand, CommandError

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
            self.set_tags(instance, options['filename'])
        else:
            # setone command
            if options.get('tag_id') is None:
                raise CommandError('You must supply the tag id argument with "setone"!')
            self.set_tagone(instance, options['tag_id'], options['filename'])

    def set_tags(self, instance, filename):
        for tid,users in self.read_user_tag(filename).items():
            self.tag_users(instance, tid, users)

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
