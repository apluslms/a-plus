import datetime

from django.core.management.base import BaseCommand
from django.utils import timezone

from notification.models import Notification


class Command(BaseCommand):
    help = ("Delete notifications. The parameters define how old notifications "
            "are deleted and if unseen notifications should be deleted "
            "in addition to seen notifications.")

    def add_arguments(self, parser):
        parser.add_argument(
            '-d',
            '--older-than-days',
            default=30,
            type=int,
            metavar='N',
            help="Delete notifications that are older than N days. By default, 30 days.",
        )
        parser.add_argument(
            '-t',
            '--until',
            type=datetime.datetime.fromisoformat,
            metavar='YYYY-MM-DD HH:MM:SS +HH:MM',
            help="Delete notifications that are older than the given date. "
                 "This option overrides the '--older-than-days' option. "
                 "Give the timestamp in the ISO 8601 format: YYYY-MM-DD HH:MM:SS +HH:MM. "
                 "If you do not specify the timezone, UTC +00:00 is assumed.",
        )
        parser.add_argument(
            '-u',
            '--delete-unseen',
            action='store_true',
            help="Delete unseen notifications in addition to seen notifications.",
        )

    def handle(self, *args, **options):
        until = options['until']
        if not until:
            until = timezone.now() - datetime.timedelta(days=options['older_than_days'])
        elif until.tzinfo is None: # naive datetime, make it normal time UTC +0
            until = until.replace(tzinfo=datetime.timezone.utc)
        conditions = {
            'timestamp__lt': until,
            'seen': True,
        }
        if options['delete_unseen']:
            del conditions['seen']

        num_deleted, num_deleted_by_type = Notification.objects.filter(**conditions).delete()
        if num_deleted == 0:
            self.stdout.write("No notifications deleted.")
        else:
            for typ, n in num_deleted_by_type.items():
                self.stdout.write('Deleted {rows} rows from table {table}.'.format(
                    rows=n,
                    table=typ,
                ))
