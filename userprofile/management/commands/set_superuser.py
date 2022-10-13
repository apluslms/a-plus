from django.core.management.base import BaseCommand

from userprofile.models import User


class Command(BaseCommand):
    help = 'Will set is_superuser and is_staff for an user'

    def add_arguments(self, parser):
        parser.add_argument('-f', '--first-name')
        parser.add_argument('-l', '--last-name')
        parser.add_argument('-e', '--email')

    def handle(self, *args, **options):
        filters = {}
        for arg in ('first_name', 'last_name', 'email'):
            if options[arg]:
                filters[arg] = options[arg]
        query = User.objects.filter(**filters).all()
        count = query.count()
        user = None
        if count > 20:
            self.stdout.write(self.style
                .ERROR("Found {} users, so not printing them here. Use arguments to filter."
                .format(count))
            )
        elif count > 1:
            users = list(query)
            for i, user in enumerate(users):
                self.stdout.write(" {}: {}".format(i, user))
            selection = int(input("Select user by number: "))
            user = users[selection]
        elif count == 1:
            user = query.first()
        else:
            self.stdout.write(self.style.ERROR("No users found"))

        if user is not None:
            user.is_superuser = True
            user.is_staff = True
            user.save()
            self.stdout.write(self.style.SUCCESS("User {} is now a superuser".format(user)))
