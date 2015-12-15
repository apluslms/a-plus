from base64 import b64encode

from tastypie import fields
from tastypie.authentication import Authentication, ApiKeyAuthentication
from tastypie.authorization import ReadOnlyAuthorization
from tastypie.resources import ModelResource, ALL

from api.permissions import SuperuserAuthorization

from .models import LearningObject, BaseExercise, Submission


class LearningObjectResource(ModelResource):
    class Meta:
        queryset = LearningObject.objects.all()
        resource_name = 'learning_object'
        excludes = []

        # In the first version GET (read only) requests are
        # allowed and no authentication is required
        allowed_methods = ['get']
        authentication = Authentication()
        authorization = ReadOnlyAuthorization()


class ExerciseResource(ModelResource):
    submissions = fields.ToManyField('exercise.api.SubmissionResource', 'submissions')

    class Meta:
        queryset = BaseExercise.objects.all()
        resource_name = 'exercise'
        excludes = ['allow_assistant_grading', 'description', 'content']

        # In the first version GET (read only) requests are
        # allowed and no authentication is required
        allowed_methods = ['get']
        authentication = Authentication()
        authorization = ReadOnlyAuthorization()


class SubmissionResource(ModelResource):
    exercise = fields.ToOneField('exercise.api.ExerciseResource', 'exercise')
    grader = fields.ToOneField('userprofile.api.UserProfileResource', 'grader', null=True, blank=True)
    submitters = fields.ToManyField('userprofile.api.UserProfileResource', 'submitters', null=True, blank=True)

    def dehydrate(self, bundle):
        """
        This method iterates over the URLs of the files submitted with each
        submission and adds them in the file_urls lists of submissions.
        """
        file_urls = []
        for file in bundle.obj.files.all():
            file_urls.append(file.get_absolute_url())
        bundle.data.update({"files": file_urls})
        return bundle

    class Meta:
        queryset = Submission.objects.all()
        resource_name = 'submission'
        excludes = ['feedback']
        allowed_methods = ['get']
        include_absolute_url = True

        # Rules that enable filtering based on exercise, grader, submitter and grade.
        filtering = {
            "exercise": ('exact',),
            "grader": ('exact',),
            "submitters": ('exact',),
            "grade": ALL,
            "id": ALL
        }

        # In this version only superusers are allowed to access
        # submissions.
        authorization = SuperuserAuthorization()


class SubmissionContentResource(ModelResource):
    """
    Otherwise similar to SubmissionResource, expect submitted files are
    included (base64 encoded) and this resource can be read with
    API key authentication.
    """
    exercise = fields.ToOneField('exercise.api.ExerciseResource', 'exercise')
    grader = fields.ToOneField('userprofile.api.UserProfileResource',
        'grader', null=True, blank=True)
    submitters = fields.ToManyField('userprofile.api.UserProfileResource',
        'submitters', null=True, blank=True)

    def dehydrate(self, bundle):
        """
        Add the content of submitted files with base64 encoding, as well as,
        the student ids of the submitters.
        """
        file_contents = {}
        for file in bundle.obj.files.all():
            file_contents[file.filename] = b64encode(file.file_object.read())
        bundle.data.update({"files": file_contents})

        student_ids = []
        for submitter in bundle.obj.submitters.all():
            student_ids.append(submitter.student_id)
        bundle.data.update({"student_ids": student_ids})

        return bundle

    class Meta:
        queryset = Submission.objects.all()
        resource_name = 'submission_content'
        excludes = ['feedback']
        allowed_methods = ['get']
        include_absolute_url = True

        # Rules that enable filtering based on exercise, grader, submitter and grade.
        filtering = {
            "exercise": ('exact',),
            "grader": ('exact',),
            "submitters": ('exact',),
            "grade": ALL,
            "id": ALL
        }

        authentication = ApiKeyAuthentication()
        authorization = ReadOnlyAuthorization()
