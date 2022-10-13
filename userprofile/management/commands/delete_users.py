import datetime

from django.contrib.auth.models import User # pylint: disable=imported-auth-user
from django.core.management.base import BaseCommand
from django.db.models.query import QuerySet
from course.models import CourseInstance
from django.utils import timezone


class Command(BaseCommand):
    help = 'Delete inactive users based on the last_login timestamp, and course enrollment status'

    def add_arguments(self, parser):
        parser.add_argument(
            '-d', '--days-ago', type=int, default=365,
            help='Speficy number of days of inactivity required for deleting user. '
            'By default, the last 365 days are used. Provide the number of days as a whole number.'
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Do not delete anything, but show which users would be deleted.',
        )

    def handle(self, *args, **options):
        since_delta = datetime.timedelta(days=options['days_ago'])
        since = timezone.now() - since_delta
        users: QuerySet[User] = User.objects.filter(last_login__lte=since)

        if options['dry_run']:
            self.stdout.write('This is just a dry run. Nothing will be deleted.')

        for u in users:
            # Is user active in any role on any course instance? Admins are ignored.
            if not CourseInstance.objects.get_active(u.userprofile).exists() and not u.is_superuser:
                self.stdout.write(f"Deleting user {u.username}")
                if not options['dry_run']:
                    u.delete()
