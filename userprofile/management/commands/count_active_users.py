import datetime

from django.contrib.auth.models import User # pylint: disable=imported-auth-user
from django.core.management.base import BaseCommand
from django.utils import timezone


class Command(BaseCommand):
    help = 'Count active users based on the last_login timestamp'

    def add_arguments(self, parser):
        parser.add_argument(
            '-d', '--days-ago', type=int, default=365,
            help='Count the number of users who have logged in in the past N days. '
            'By default, the last 365 days are used. Provide the number of days as a whole number.'
        )

    def handle(self, *args, **options):
        since_delta = datetime.timedelta(days=options['days_ago'])
        since = timezone.now() - since_delta
        num_users = User.objects.filter(last_login__gte=since).count()
        self.stdout.write("{0} users have logged in since {1}".format(num_users, since))
