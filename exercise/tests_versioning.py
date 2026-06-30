from time import time
from unittest.mock import Mock, patch

from django.core.cache import cache
from django.test import SimpleTestCase
from django.utils.translation import override

from lib.remote_page import RemotePageNotModified
from .async_views import _post_async_submission
from .cache.exercise import ExerciseCache
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


class FeedbackVersionTest(SimpleTestCase):
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
