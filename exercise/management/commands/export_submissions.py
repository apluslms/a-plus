import csv
import sys

from django.core.management.base import BaseCommand
from django.db.models import Prefetch

from course.models import CourseModule
from deviations.models import DeadlineRuleDeviation, MaxSubmissionsRuleDeviation
from ...models import BaseExercise, Submission
from userprofile.models import UserProfile


class Command(BaseCommand):
    help = 'Exports submission and exercise data from given course instances into CSV files'

    def add_arguments(self, parser):
        parser.add_argument(
            'course_instance_id',
            nargs='+',
            type=int,
            help='Course instance id (from model CourseInstance) whose data is exported',
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

    def handle(self, *args, **options):
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

        # Fetch all exercises from the given course instances.
        exercises = BaseExercise.objects.filter(
            course_module__course_instance__pk__in=course_instance_ids,
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
            submissions = Submission.objects.filter(
                exercise__in=exercises,
            ).prefetch_related(
                Prefetch(
                    'submitters',
                    queryset=UserProfile.objects.select_related('user').only('user__id'),
                    to_attr='submitter_userprofiles',
                ),
            ).defer(
                'hash',
                'grader',
                'feedback',
                'assistant_feedback',
                'submission_data',
                'grading_data',
                'meta_data',
            ).order_by(
                'id',
            )[submissions_slice]

            # Fetch all deadline deviations in the course instances.
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

            all_deadline_deviations = {}
            for dl_dev in all_deadline_deviations_queryset:
                all_deadline_deviations.setdefault(dl_dev.exercise.id, {})[dl_dev.submitter.user.id] = dl_dev.get_new_deadline()

            # Fetch all max submissions deviations in the course instances.
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

            all_max_submissions_deviations = {}
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
            self.write_submission_csv(
                submission_file_path,
                submissions,
                all_deadline_deviations,
                all_max_submissions_deviations,
            )
            self.stdout.write("Created the submission file: " + submission_file_path)


    def write_exercise_csv(self, exercise_file_path, exercises):
        with open(exercise_file_path, 'w', newline='') as f:
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


    def write_submission_csv(
            self,
            submission_file_path,
            submissions,
            all_deadline_deviations,
            all_max_submissions_deviations,
    ):
        with open(submission_file_path, 'w', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=(
                'submission_id',
                'submitter_user_ids',
                'exercise_id',
                'submission_time',
                'personal_deadline',
                'personal_max_submissions',
                'grade',
                'service_points',
                'service_max_points',
                'status',
                'late_penalty_applied',
                'grading_time',
            ))
            writer.writeheader()
            for submission in submissions:
                dl_deviations = all_deadline_deviations.get(submission.exercise.pk, {})
                personal_deadline = None
                for profile in submission.submitter_userprofiles:
                    dl = dl_deviations.get(profile.user.id, None)
                    if dl is not None and (
                            personal_deadline is None
                            or dl > personal_deadline
                    ):
                        personal_deadline = dl

                max_submissions_deviations = all_max_submissions_deviations.get(submission.exercise.pk, {})
                personal_max_submissions = None
                for profile in submission.submitter_userprofiles:
                    max_sbms = max_submissions_deviations.get(profile.user.id, None)
                    if max_sbms is not None and (
                            personal_max_submissions is None
                            or max_sbms > personal_max_submissions
                    ):
                        personal_max_submissions = max_sbms

                writer.writerow({
                    'submission_id': submission.pk,
                    'submitter_user_ids': '-'.join([str(profile.user.id) for profile in submission.submitter_userprofiles]),
                    'exercise_id': submission.exercise.pk,
                    'submission_time': submission.submission_time,
                    'personal_deadline': personal_deadline,
                    'personal_max_submissions': personal_max_submissions,
                    'grade': submission.grade,
                    'service_points': submission.service_points,
                    'service_max_points': submission.service_max_points,
                    'status': submission.status,
                    'late_penalty_applied': submission.late_penalty_applied,
                    'grading_time': submission.grading_time,
                })

