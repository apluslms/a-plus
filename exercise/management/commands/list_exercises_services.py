from datetime import timedelta
from json import dumps
from urllib.parse import urlsplit

from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone

from exercise.models import LearningObject
from lib.localization_syntax import parse_localized


class Command(BaseCommand):
    help = 'Collects information about exercise services courses use'

    def add_arguments(self, parser):
        parser.add_argument('-f', '--format', metavar='FORMAT',
            default='plain',
            help="Set output format (default: plain). "
                 "Can be set to 'json' for machine readable output.")
        parser.add_argument('-a', '--max-age', metavar='DAYS',
            help="Limit results to courses, which have started within given "
                 "time. Value is days be default, but you may use suffixes: "
                 "m for months and y for years.")
        parser.add_argument('-V', '--visible', action='store_true',
            help="Limit results to courses, which are currently visible "
                 "to students")

    def handle(self, *args, **options):
        services = {}
        content_types = {}

        # all object, which do have a service_url
        qs = LearningObject.objects.exclude(service_url='')

        # limit with max age
        after = options.get('max_age')
        if after:
            try:
                num = float(after)
            except ValueError:
                num, suffix = after[:-1], after[-1]
                suffixes = {'d': 1, 'm': 30, 'y': 365}
                try:
                    num = float(num)
                except ValueError:
                    raise CommandError("Invalid value '%s' for --max-age" %
                        (after,))
                if suffix not in suffixes:
                    raise CommandError("Unknown suffix in --max-age=%s; valid: %s" %
                        (after, ', '.join(k for k in suffixes.keys())))
                num = num * suffixes[suffix]
            after = timezone.now() - timedelta(days=num)
            qs = qs.filter(course_module__course_instance__starting_time__gt=after)

        # limit with visibility
        if options.get('visible'):
            qs = qs.filter(course_module__course_instance__visible_to_students=True)

        # group
        for lo in qs.all():
            # track content type
            cid = lo.content_type_id
            if cid not in content_types:
                content_types[cid] = lo.content_type.model_class().__name__

            course = str(lo.course_module.course_instance)

            service_urls = parse_localized(lo.service_url)
            if content_types[cid] == 'LTIExercise':
                urls = [lo.get_service_url(lang) for lang, url in service_urls]
            else:
                urls = [url for lang, url in service_urls]
            domains = set(urlsplit(url).netloc for url in urls)

            for domain in domains:
                service = services.setdefault(domain, {})
                service_cont = service.setdefault(cid, {})
                service_cont[course] = service_cont.get(course, 0) + 1

        # calculate sums
        domains = list(services.keys())
        domains.sort()
        results = []
        for domain in domains:
            service = services[domain]

            cid_stats = []
            for cid, service_cont in service.items():
                total_count = sum(service_cont.values())
                courses_count = len(service_cont)

                cid_stats.append((cid, total_count, courses_count, service_cont))
            cid_stats.sort(key=lambda x: (x[1], x[2]), reverse=True)

            total=sum(x[1] for x in cid_stats)
            results.append((domain, total, cid_stats))

        results.sort(key=lambda x: (x[1], x[0]), reverse=True)

        # Collect results to a data object
        data = {
            'not_before': str(after),
        }
        data['exercises'] = exercises_by_domain = []
        for domain, total, cid_stats in results:
            domain_data = {
                'domain': domain,
                'exercises_count': sum(x[1] for x in cid_stats),
            }
            domain_data['exercises'] = exercises_for_domain = []
            exercises_by_domain.append(domain_data)
            for cid, total_count, courses_count, service_cont in cid_stats:
                content_type = content_types[cid]
                exercise_data = {
                    'type': content_type,
                    'exercises_count': total_count,
                    'courses_count': courses_count,
                }
                exercise_data['courses'] = [
                    {
                        'name': course,
                        'exercises_count': count,
                    }
                    for course, count in sorted(
                        service_cont.items(),
                        key=lambda x: x[1],
                        reverse=True,
                    )
                ]
                exercises_for_domain.append(exercise_data)

        # Export results
        if options.get('format') == 'json':
            # Export as json
            self.stdout.write(dumps(data))
        else:
            # Export as plain / human readable
            print("Listing exercise statistics from courses started after {after}\n".format(
                after=data['not_before'],
            ))
            for domain in data['exercises']:
                print("{total:4d} exercises on {domain}".format(
                    domain=domain['domain'],
                    total=domain['exercises_count'],
                ))
                for exercise in domain['exercises']:
                    print("    {exercises:4d} of {type}: {courses} courses".format(
                        type=exercise['type'],
                        exercises=exercise['exercises_count'],
                        courses=exercise['courses_count'],
                    ))
                    for course in exercise['courses'][:3]:
                        print("        {count:4d} {course}".format(
                            course=course['name'],
                            count=course['exercises_count'],
                        ))
