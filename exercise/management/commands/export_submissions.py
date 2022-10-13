import csv
import sys

from django.core.management.base import BaseCommand, CommandError
from django.db.models import Count, Max, Min, Prefetch, Q

from course.models import CourseModule
from deviations.models import DeadlineRuleDeviation, MaxSubmissionsRuleDeviation
from ...models import BaseExercise, Submission
from userprofile.models import UserProfile


class Command(BaseCommand):
    help = 'Exports submission and exercise data from given course instances into CSV files'

    def add_arguments(self, parser):
        parser.add_argument(
            'course_instance_id',
            nargs='*',
            type=int,
            help='Course instance id (from model CourseInstance) whose data is exported',
        )
        parser.add_argument(
            '-f',
            '--include-exercises-file',
            help='Include only exercises (and their submissions) whose BaseExercise ids '
                 'are listed in the given file (comma separated). '
                 'The parameter "course_instance_id" may not be used with this option.',
        )
        parser.add_argument(
            '-e',
            '--exercise-output-file',
            help='Exercises are written to this CSV file. The file is created or overwritten. '
                 'If you do not set any value, then no exercise file is written.',
        )
        parser.add_argument(
            '-s',
            '--submission-output-file',
            help='Submissions are written to this CSV file. The file is created or overwritten. '
                 'If you do not set any value, then no submission file is written.',
        )
        parser.add_argument(
            '-o',
            '--submission-results-format',
            action='store_true',
            help="If set, changes the format of the output submissions CSV file. "
                 "The output contains only aggregate results, one row per exercise per student: "
                 "final grade, number of submissions, timestamps of the first and last submissions.",
        )
        parser.add_argument(
            '-b',
            '--limit-submissions-start',
            type=int,
            help='Limit the number of submissions that are written to the CSV file. '
                 'This is the start index of the submissions. '
                 'By default, all submissions starting from index zero are included.',
        )
        parser.add_argument(
            '-l',
            '--limit-submissions-end',
            type=int,
            help='Limit the number of submissions that are written to the CSV file. '
                 'This is the end index of the submissions. '
                 'By default, all submissions up to the last index are included.',
        )
        parser.add_argument(
            '-d',
            '--include-deadline-deviations',
            action='store_true',
            help="If set, students' personal deadline deviations are included in the submissions CSV file.",
        )
        parser.add_argument(
            '-m',
            '--include-max-submission-deviations',
            action='store_true',
            help=(
                "If set, students' personal max submission attempt deviations are "
                "included in the submissions CSV file."
            ),
        )
        parser.add_argument(
            '-i',
            '--include-student-ids',
            action='store_true',
            help="If set, submitters' student ids are included in the submissions CSV file.",
        )
        parser.add_argument(
            '-u',
            '--exclude-user-ids',
            action='store_true',
            help="If set, submitters' user ids are excluded from the submissions CSV (included by default).",
        )
        parser.add_argument(
            '-x',
            '--exclude-exercises-file',
            help='Exclude these exercises. This should be used with the "course_instance_id" parameter. '
                 'The BaseExercise ids are defined as a comma-separated list in the given file.',
        )
        parser.add_argument(
            '-r',
            '--include-users-file',
            help="Include submissions only from these users whose User ids "
                 "are listed in the given file (comma separated).",
        )

    def parse_comma_list_file(self, file_path):
        try:
            with open(file_path, 'r', encoding="utf-8") as f:
                return [val.strip() for val in f.read().split(',') if val.strip()]
        except OSError as e:
            raise CommandError(f'Error in reading the file "{file_path}".') from e

    def handle(self, *args, **options): # noqa: MC0001
        course_instance_ids = options['course_instance_id']

        exercise_file_path = options['exercise_output_file']
        submission_file_path = options['submission_output_file']
        if not exercise_file_path and not submission_file_path:
            self.stderr.write(
                'At least one of the options "--exercise-output-file" or '
                '"--submission-output-file" must be given in order to output anything.'
            )
            self.stderr.write('Aborting...')
            sys.exit(2)

        limit_submissions_start = options['limit_submissions_start']
        limit_submissions_end = options['limit_submissions_end']
        if limit_submissions_start is not None and limit_submissions_start < 0:
            self.stderr.write("--limit-submissions-start must be a non-negative integer.")
            sys.exit(2)
        if limit_submissions_end is not None and limit_submissions_end < 0:
            self.stderr.write("--limit-submissions-end must be a non-negative integer.")
            sys.exit(2)
        submissions_slice = slice(limit_submissions_start, limit_submissions_end)

        exercise_filters = {}
        if course_instance_ids:
            exercise_filters['course_module__course_instance__pk__in'] = course_instance_ids

        if options['include_exercises_file']:
            exercise_filters['pk__in'] = self.parse_comma_list_file(options['include_exercises_file'])

        if not exercise_filters:
            raise CommandError(
                'Either the "course_instance_id" parameter '
                'or the "include_exercises_file" option must be specified.',
            )
        if len(exercise_filters) > 1:
            raise CommandError('Only one of "course_instance_id" or "include_exercises_file" may be specified.')

        exercise_q_filters = []
        if options['exclude_exercises_file']:
            exercise_q_filters.append(~Q(pk__in=self.parse_comma_list_file(options['exclude_exercises_file'])))

        # Fetch all exercises from the given course instances.
        exercises = BaseExercise.objects.filter(
            *exercise_q_filters,
            **exercise_filters,
        ).select_related(
            'category',
        ).prefetch_related(
            Prefetch(
                'course_module',
                queryset=CourseModule.objects.select_related(
                    'course_instance',
                ).only(
                    'order',
                    'points_to_pass',
                    'closing_time',
                    'late_submissions_allowed',
                    'late_submission_deadline',
                    'late_submission_penalty',
                    'course_module__course_instance__instance_name',
                    'course_module__course_instance__url',
                ),
            ),
        ).defer(
            'description',
            'service_url',
            'exercise_info',
            'model_answers',
            'templates',
            'content',
            'category__status',
            'category__description',
            'category__course_instance',
        ).order_by(
            'id',
        )

        # Fetch all submissions for the exercises.
        if submission_file_path:
            include_user_ids = None
            if options['include_users_file']:
                include_user_ids = self.parse_comma_list_file(options['include_users_file'])

            submission_filters = {
                'exercise__in': exercises,
            }
            if include_user_ids:
                submission_filters['submitters__user_id__in'] = include_user_ids

            user_fields = ['user__id']
            if options['include_student_ids'] or options['submission_results_format']:
                user_fields.append('student_id')

            submissions = Submission.objects.filter(
                **submission_filters,
            )
            if not options['exclude_user_ids'] or options['include_student_ids'] or include_user_ids:
                submissions = submissions.prefetch_related(
                    Prefetch(
                        'submitters',
                        queryset=UserProfile.objects.select_related('user').only(*user_fields),
                        to_attr='submitter_userprofiles',
                    ),
                )
            if options['submission_results_format']:
                # Aggregate exercise results.
                submissions = submissions.exclude(status__in=(
                    Submission.STATUS.UNOFFICIAL,
                    Submission.STATUS.ERROR,
                    Submission.STATUS.REJECTED,
                )).values(
                    'submitters__user_id',
                    'exercise_id',
                    'submitters__student_id',
                ).annotate(
                    count=Count('id'),
                    first_timestamp=Min('submission_time'),
                    last_timestamp=Max('submission_time'),
                ).annotate_submitter_points('total')
            else:
                submissions = submissions.defer(
                    'hash',
                    'grader',
                    'feedback',
                    'assistant_feedback',
                    'submission_data',
                    'grading_data',
                    'meta_data',
                )
            submissions = submissions.order_by()[submissions_slice]

            all_deadline_deviations = {}
            if options['include_deadline_deviations']:
                # Fetch all deadline deviations in the course instances.
                # TODO: this does not use the "include_exercises_file" or "exclude_exercises_file" options at all.
                all_deadline_deviations_queryset = DeadlineRuleDeviation.objects.filter(
                    exercise__course_module__course_instance__id__in=course_instance_ids,
                ).prefetch_related(
                    Prefetch(
                        'exercise',
                        queryset=BaseExercise.objects.select_related(
                            'course_module',
                        ).only(
                            'id',
                            'course_module__id',
                            'course_module__closing_time',
                            'course_module__course_instance__id',
                            'course_module__course_instance__course__id',
                        ),
                    ),
                    Prefetch(
                        'submitter',
                        queryset=UserProfile.objects.select_related('user').only('user__id'),
                    ),
                ).only(
                    'exercise__id',
                    'exercise__course_module__closing_time',
                    'exercise__course_module__course_instance__id',
                    'submitter__user__id',
                    'extra_minutes',
                )

                for dl_dev in all_deadline_deviations_queryset:
                    all_deadline_deviations.setdefault(
                        dl_dev.exercise.id, {}
                    )[dl_dev.submitter.user.id] = dl_dev.get_new_deadline()

            all_max_submissions_deviations = {}
            if options['include_max_submission_deviations']:
                # Fetch all max submissions deviations in the course instances.
                # TODO: this does not use the "include_exercises_file" or "exclude_exercises_file" options at all.
                all_max_submissions_deviations_queryset = MaxSubmissionsRuleDeviation.objects.filter(
                    exercise__course_module__course_instance__id__in=course_instance_ids,
                ).select_related(
                    'exercise',
                ).prefetch_related(
                    Prefetch(
                        'submitter',
                        queryset=UserProfile.objects.select_related('user').only('user__id'),
                    ),
                ).only(
                    'exercise__id',
                    'exercise__max_submissions',
                    'submitter__user__id',
                    'extra_submissions',
                )

                for sbms_dev in all_max_submissions_deviations_queryset:
                    all_max_submissions_deviations.setdefault(
                        sbms_dev.exercise.id,
                        {},
                    )[sbms_dev.submitter.user.id] = sbms_dev.exercise.max_submissions + sbms_dev.extra_submissions

        # Create the CSV output files.
        # One CSV file for all exercises.
        if exercise_file_path:
            self.write_exercise_csv(exercise_file_path, exercises)
            self.stdout.write("Created the exercise file: " + exercise_file_path)

        # One CSV file for all submissions.
        if submission_file_path:
            if options['submission_results_format']:
                self.write_results_csv(
                    submission_file_path,
                    submissions,
                    options['include_student_ids'],
                    not options['exclude_user_ids'],
                )
            else:
                self.write_submission_csv(
                    submission_file_path,
                    submissions,
                    all_deadline_deviations,
                    all_max_submissions_deviations,
                    options['include_deadline_deviations'],
                    options['include_max_submission_deviations'],
                    options['include_student_ids'],
                    not options['exclude_user_ids'],
                )
            self.stdout.write("Created the submission file: " + submission_file_path)


    def write_results_csv(self, csv_file_path, submissions, include_student_ids=True, include_user_ids=True):
        # submissions is an iterable of dictionaries, one dict per exercise per submitter.
        with open(csv_file_path, 'w', newline='', encoding="utf-8") as f:
            fieldnames = [
                'exercise_id',
                'num_submissions',
                'final_points',
                'first_timestamp',
                'last_timestamp',
            ]
            if include_student_ids:
                fieldnames.insert(1, 'student_id')
            if include_user_ids:
                fieldnames.insert(1, 'user_id')
            writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction='ignore')
            writer.writeheader()
            for submission in submissions:
                writer.writerow({
                    'exercise_id': submission['exercise_id'],
                    'user_id': submission['submitters__user_id'],
                    'student_id': submission['submitters__student_id'],
                    'num_submissions': submission['count'],
                    'final_points': submission['total'],
                    'first_timestamp': submission['first_timestamp'],
                    'last_timestamp': submission['last_timestamp'],
                })


    def write_exercise_csv(self, exercise_file_path, exercises):
        with open(exercise_file_path, 'w', newline='', encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=(
                'id',
                'name',
                'course_instance',
                'deadline',
                'late_submissions_allowed',
                'late_submission_deadline',
                'late_submission_penalty',
                'max_points',
                'max_submissions',
                'category', # the name of the category
                'difficulty',
                'points_to_pass',
                'status',
            ))
            writer.writeheader()
            for exercise in exercises:
                writer.writerow({
                    'id': exercise.pk,
                    'name': exercise.name, # NB: this does not include any hierarchical numbering 1.2.3
                    'course_instance': exercise.course_module.course_instance.instance_name,
                    'deadline': exercise.course_module.closing_time,
                    'late_submissions_allowed': exercise.course_module.late_submissions_allowed,
                    'late_submission_deadline': exercise.course_module.late_submission_deadline,
                    'late_submission_penalty': exercise.course_module.late_submission_penalty,
                    'max_points': exercise.max_points,
                    'max_submissions': exercise.max_submissions,
                    'category': exercise.category.name,
                    'difficulty': exercise.difficulty,
                    'points_to_pass': exercise.points_to_pass,
                    'status': exercise.status,
                })


    def write_submission_csv( # pylint: disable=too-many-locals too-many-arguments
            self,
            submission_file_path,
            submissions,
            all_deadline_deviations,
            all_max_submissions_deviations,
            include_deadline_deviations=False,
            include_max_submission_deviations=False,
            include_student_ids=False,
            include_user_ids=True,
    ):
        fieldnames = [
            'submission_id',
            'exercise_id',
            'submission_time',
            'grade',
            'service_points',
            'service_max_points',
            'status',
            'late_penalty_applied',
            'grading_time',
            'marked_as_final',
        ]
        if include_user_ids:
            fieldnames.insert(2, 'submitter_user_ids')
        if include_student_ids:
            fieldnames.insert(2, 'student_ids')
        if include_max_submission_deviations:
            fieldnames.append('personal_max_submissions')
        if include_deadline_deviations:
            fieldnames.append('personal_deadline')

        with open(submission_file_path, 'w', newline='', encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            for submission in submissions:
                d = {
                    'submission_id': submission.pk,
                    'exercise_id': submission.exercise.pk,
                    'submission_time': submission.submission_time,
                    'grade': submission.grade,
                    'service_points': submission.service_points,
                    'service_max_points': submission.service_max_points,
                    'status': submission.status,
                    'late_penalty_applied': submission.late_penalty_applied,
                    'grading_time': submission.grading_time,
                    'marked_as_final': submission.force_exercise_points,
                }
                if include_user_ids:
                    d['submitter_user_ids'] = '-'.join(
                        [str(profile.user.id) for profile in submission.submitter_userprofiles]
                    )
                if include_student_ids:
                    d['student_ids'] = '-'.join(
                        [str(profile.student_id) for profile in submission.submitter_userprofiles]
                    )

                if include_deadline_deviations:
                    dl_deviations = all_deadline_deviations.get(submission.exercise.pk, {})
                    personal_deadline = None
                    for profile in submission.submitter_userprofiles:
                        dl = dl_deviations.get(profile.user.id, None)
                        if dl is not None and (
                                personal_deadline is None
                                or dl > personal_deadline
                        ):
                            personal_deadline = dl

                    d['personal_deadline'] = personal_deadline

                if include_max_submission_deviations:
                    max_submissions_deviations = all_max_submissions_deviations.get(submission.exercise.pk, {})
                    personal_max_submissions = None
                    for profile in submission.submitter_userprofiles:
                        max_sbms = max_submissions_deviations.get(profile.user.id, None)
                        if max_sbms is not None and (
                                personal_max_submissions is None
                                or max_sbms > personal_max_submissions
                        ):
                            personal_max_submissions = max_sbms

                    d['personal_max_submissions'] = personal_max_submissions

                writer.writerow(d)
