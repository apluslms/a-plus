from time import time
from unittest.mock import Mock, patch

from django.core.cache import cache
from django.test import SimpleTestCase, TestCase
from django.utils.translation import override

from lib.remote_page import RemotePageNotModified
from .async_views import _post_async_submission
from .cache.exercise import ExerciseCache
from .models import Submission
from .protocol.aplus import load_feedback_page
from .views import ExerciseView


class ExerciseCacheVersionTest(SimpleTestCase):
    def tearDown(self):
        cache.clear()

    def test_versionless_cache_entry_forces_full_response(self):
        exercise = Mock()
        page = Mock(
            content="new content",
            head="",
            last_modified="new timestamp",
            exercise_version="new version",
            expires=time() + 60,
            is_loaded=True,
        )

        def load_page(*args, last_modified=None):
            if last_modified:
                raise RemotePageNotModified(time() + 60)
            return page

        exercise.load_page.side_effect = load_page
        exercise_cache = ExerciseCache.__new__(ExerciseCache)
        exercise_cache.load_args = ["en", Mock(), [], "exercise", None]
        old_data = {
            "head": "",
            "content": b"old content",
            "last_modified": "old timestamp",
            "expires": time() + 60,
        }

        data = exercise_cache._generate_data(exercise, old_data)

        self.assertEqual(data["exercise_version"], "new version")
        self.assertIsNone(exercise.load_page.call_args.kwargs["last_modified"])

    def test_cached_version_is_returned_for_randomized_exercise(self):
        cache.set(
            ExerciseCache._key(123, modifiers=["en"]),
            (time(), {"exercise_version": "version", "expires": 0}),
        )

        version = ExerciseCache.cached_exercise_version(123, "en")

        self.assertEqual(version, "version")


class FeedbackVersionTest(TestCase):
    def test_grader_response_version_is_stored_and_invalidates_old_page(self):
        exercise = Mock()
        exercise.course_instance.id = 1
        exercise.course_instance.default_language = "en"
        exercise.course_instance.visible_to_students = False
        submission = Mock()
        submission.lang = "en"
        submission.meta_data = {"lang": "en"}
        submission.get_post_parameters.return_value = ({}, {})

        def set_page_data(page, _remote_page, _parsed_exercise):
            page.is_loaded = True
            page.is_rejected = True
            page.clean_content = "feedback"
            page.exercise_version = "new version"

        with (
            patch("exercise.protocol.aplus.RemotePage"),
            patch("exercise.protocol.aplus.parse_page_content", side_effect=set_page_data),
            patch.object(ExerciseCache, "cached_exercise_version", return_value="old version"),
            patch.object(ExerciseCache, "invalidate") as invalidate,
        ):
            load_feedback_page(Mock(), "https://grader.example/exercise", exercise, submission)

        self.assertEqual(submission.meta_data["exercise_version"], "new version")
        invalidate.assert_called_once_with(exercise, modifiers=["en"])
        submission.save.assert_called_once_with()

    def test_remote_feedback_does_not_revive_invalidated_submission(self):
        exercise = Mock()
        submission = Mock(status=Submission.STATUS.READY)
        submission.STATUS = Submission.STATUS
        submission.get_post_parameters.return_value = ({}, {})

        def invalidate_during_request(page, _remote_page, _exercise):
            page.is_loaded = True
            page.is_rejected = True
            submission.status = Submission.STATUS.INVALIDATED

        with (
            patch("exercise.protocol.aplus.RemotePage"),
            patch("exercise.protocol.aplus.parse_page_content", side_effect=invalidate_during_request),
        ):
            load_feedback_page(Mock(), "https://grader.example/exercise", exercise, submission)

        submission.refresh_from_db.assert_called_once_with(fields=['status'])
        submission.set_rejected.assert_not_called()
        submission.save.assert_not_called()

    def test_async_grader_response_version_is_stored(self):
        exercise = Mock()
        exercise.course_instance.default_language = "en"
        exercise.course_instance.visible_to_students = False
        submission = Mock(
            lang="en",
            lti_launch_id=None,
            meta_data={"lang": "en"},
        )
        request = Mock()
        request.POST = {
            "points": "1",
            "max_points": "1",
            "feedback": "feedback",
            "exercise_version": "new version",
        }

        with (
            patch.object(ExerciseCache, "cached_exercise_version", return_value="old version"),
            patch.object(ExerciseCache, "invalidate") as invalidate,
        ):
            result = _post_async_submission(request, exercise, submission)

        self.assertTrue(result["success"])
        self.assertEqual(submission.meta_data["exercise_version"], "new version")
        invalidate.assert_called_once_with(exercise, modifiers=["en"])
        submission.save.assert_called_once_with()

    def test_async_grader_does_not_save_if_invalidated_during_processing(self):
        exercise = Mock()
        exercise.course_instance.default_language = "en"
        submission = Mock(
            status=Submission.STATUS.READY,
            lang="en",
            meta_data={"lang": "en"},
        )
        submission.STATUS = Submission.STATUS
        request = Mock()
        request.POST = {
            "points": "1",
            "max_points": "1",
            "feedback": "feedback",
            "exercise_version": "new version",
        }

        def invalidate_during_cache_lookup(*_args):
            submission.status = Submission.STATUS.INVALIDATED

        with patch.object(ExerciseCache, "cached_exercise_version", side_effect=invalidate_during_cache_lookup):
            result = _post_async_submission(request, exercise, submission)

        self.assertFalse(result["success"])
        submission.refresh_from_db.assert_called_once_with(fields=['status'])
        submission.set_ready.assert_not_called()
        submission.save.assert_not_called()

    def test_async_grader_stops_side_effects_if_invalidation_wins_save(self) -> None:
        exercise = Mock()
        submission = Mock(
            status=Submission.STATUS.READY,
            lti_launch_id="launch-id",
            meta_data={"lang": "en"},
        )
        submission.STATUS = Submission.STATUS
        submission.save.side_effect = lambda: setattr(submission, 'status', Submission.STATUS.INVALIDATED)
        request = Mock()
        request.POST = {
            "points": "1",
            "max_points": "1",
            "feedback": "feedback",
            "notify": "yes",
        }

        with (
            patch("exercise.async_views.Notification.send") as notify,
            patch("exercise.async_views.send_lti_points") as send_points,
        ):
            result = _post_async_submission(request, exercise, submission)

        self.assertFalse(result["success"])
        self.assertEqual(result["errors"], ["Submission has been invalidated and cannot be graded."])
        notify.assert_not_called()
        send_points.assert_not_called()

    def test_async_grader_tags_only_after_successful_save(self) -> None:
        for invalidation_check in ('refresh_from_db', 'save', None):
            with self.subTest(invalidation_check=invalidation_check):
                exercise = Mock()
                submission = Mock(
                    id=1,
                    status=Submission.STATUS.READY,
                    lti_launch_id=None,
                    meta_data={"lang": "en"},
                )
                submission.STATUS = Submission.STATUS
                if invalidation_check:
                    getattr(submission, invalidation_check).side_effect = (
                        lambda current=submission, **_kwargs: setattr(current, 'status', Submission.STATUS.INVALIDATED)
                    )
                request = Mock()
                request.POST = {
                    "points": "1",
                    "max_points": "1",
                    "feedback": "feedback",
                    "grading_data": '{"submission_tags": "grader-tag"}',
                }

                with (
                    patch("exercise.async_views.SubmissionTag.objects.get") as get_tag,
                    patch("exercise.async_views.SubmissionTagging.objects") as tagging,
                ):
                    tagging.filter.return_value.exists.return_value = False
                    tagging.create.side_effect = (
                        lambda current=submission, **_kwargs: current.save.assert_called_once_with()
                    )
                    result = _post_async_submission(request, exercise, submission)

                if invalidation_check:
                    self.assertFalse(result["success"])
                    self.assertEqual(result["errors"], ["Submission has been invalidated and cannot be graded."])
                    get_tag.assert_not_called()
                    tagging.create.assert_not_called()
                else:
                    self.assertTrue(result["success"])
                    tagging.create.assert_called_once_with(submission=submission, tag=get_tag.return_value)

    def test_remote_grader_does_not_send_lti_points_if_invalidation_wins_save(self) -> None:
        exercise = Mock(max_points=1)
        submission = Mock(status=Submission.STATUS.READY, lti_launch_id="launch-id")
        submission.STATUS = Submission.STATUS
        submission.get_post_parameters.return_value = ({}, {})
        submission.save.side_effect = lambda: setattr(submission, 'status', Submission.STATUS.INVALIDATED)

        def set_page_data(page, _remote_page, _exercise):
            page.is_loaded = True
            page.is_accepted = True
            page.points = 1
            page.max_points = 1
            page.clean_content = "feedback"

        with (
            patch("exercise.protocol.aplus.RemotePage"),
            patch("exercise.protocol.aplus.parse_page_content", side_effect=set_page_data),
            patch("exercise.protocol.aplus.send_lti_points") as send_points,
        ):
            load_feedback_page(Mock(), "https://grader.example/exercise", exercise, submission)

        send_points.assert_not_called()

    def test_async_grader_preserves_unofficial_status(self):
        exercise = Mock()
        submission = Mock(
            status=Submission.STATUS.INITIALIZED,
            lti_launch_id=None,
            meta_data={"lang": "en"},
        )
        submission.STATUS = Submission.STATUS
        submission.set_points.side_effect = lambda *_args: setattr(
            submission, 'status', Submission.STATUS.UNOFFICIAL
        )
        submission.refresh_from_db.side_effect = lambda **_kwargs: setattr(
            submission, 'status', Submission.STATUS.INITIALIZED
        )
        request = Mock()
        request.POST = {
            "points": "1",
            "max_points": "1",
            "feedback": "feedback",
        }

        result = _post_async_submission(request, exercise, submission)

        self.assertTrue(result["success"])
        self.assertEqual(submission.status, Submission.STATUS.UNOFFICIAL)
        submission.save.assert_called_once_with()


class SubmissionCompatibilityTest(SimpleTestCase):
    def setUp(self):
        self.view = ExerciseView()
        self.view.exercise = Mock()
        self.view.post_url_name = "exercise"
        self.request = Mock()
        self.students = []

    @override("en")
    def test_legacy_submission_is_kept(self):
        submission = Mock(lang="en", meta_data={})
        self.view._get_current_exercise_version = Mock()

        compatible = self.view._submission_is_compatible(
            self.request,
            self.students,
            submission,
        )

        self.assertTrue(compatible)
        self.view._get_current_exercise_version.assert_not_called()

    @override("en")
    def test_language_change_is_incompatible(self):
        submission = Mock(lang="fi", meta_data={})

        compatible = self.view._submission_is_compatible(
            self.request,
            self.students,
            submission,
        )

        self.assertFalse(compatible)

    @override("en")
    def test_version_change_is_incompatible(self):
        submission = Mock(lang="en", meta_data={"exercise_version": "old"})
        self.view._get_current_exercise_version = Mock(return_value="new")

        compatible = self.view._submission_is_compatible(
            self.request,
            self.students,
            submission,
        )

        self.assertFalse(compatible)

    @override("en")
    def test_delayed_feedback_uses_default_form_after_change(self):
        submission = Mock(lang="en", meta_data={"exercise_version": "old"})
        queryset = self.view.exercise.get_submissions_for_student.return_value
        queryset.order_by.return_value.first.return_value = submission
        self.view.exercise.is_submittable = True
        self.view.exercise.load.return_value = default_page = Mock()
        self.view.profile = Mock()
        self.view.feedback_revealed = False
        self.view._get_current_exercise_version = Mock(return_value="new")
        self.request.GET = {"submission": "true"}

        page = self.view.get_page(self.request, self.students)

        self.assertIs(page, default_page)
        submission.load.assert_not_called()

    @override("en")
    def test_version_check_reuses_loaded_default_form(self):
        submission = Mock(lang="en", meta_data={"exercise_version": "old"})
        queryset = self.view.exercise.get_submissions_for_student.return_value
        queryset.order_by.return_value.first.return_value = submission
        default_page = Mock(exercise_version="new")
        self.view.exercise.is_submittable = True
        self.view.exercise.load.return_value = default_page
        self.view.profile = Mock()
        self.view.feedback_revealed = True
        self.request.GET = {"submission": "true"}

        with patch.object(ExerciseCache, "cached_exercise_version", return_value=""):
            page = self.view.get_page(self.request, self.students)

        self.assertIs(page, default_page)
        self.view.exercise.load.assert_called_once_with(
            self.request,
            self.students,
            url_name="exercise",
        )
