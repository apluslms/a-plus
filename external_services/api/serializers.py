import logging

from django.utils import timezone

from rest_framework import serializers

from exercise.exercise_summary import UserExerciseSummary
from exercise.models import Submission
from .parsers import parse_sourced_id, LTIOutcomeXMLParser
from .renderers import LTIOutcomeResponseRenderer


logger = logging.getLogger('aplus.external_services.api')


class LTIOutcomeSerializer(serializers.Serializer):
    # parameters that are parsed from the XML of the request body
    version = serializers.CharField(default='1.0')
    msgid = serializers.CharField(max_length=127)
    req_type = serializers.ChoiceField(choices=[
        LTIOutcomeXMLParser.TYPE_REPLACE, LTIOutcomeXMLParser.TYPE_READ, LTIOutcomeXMLParser.TYPE_DELETE
    ])
    sourced_id = serializers.CharField(max_length=1024)
    score = serializers.FloatField(min_value=0, max_value=1, required=False)

    def create(self, validated_data):
        exercise = validated_data['exercise']
        submission = Submission.objects.create(
            exercise=exercise,
            status=Submission.STATUS.READY,
            grade=int(validated_data['score'] * exercise.max_points + 0.5),
            # +0.5 for rounding to the nearest integer since int() truncates down
            grading_time=timezone.now(),
            grading_data={
                'score': validated_data['score'],
                'lti_msgid': validated_data['msgid'],
                'sourced_id': validated_data['sourced_id'],
            },
        )
        # the submission must be saved before its many-to-many field submitters may be updated
        submission.submitters.add(validated_data['submitter'])
        return submission

    def to_representation(self, instance):
        '''Takes the object instance that requires serialization, and should
        return a primitive representation. Typically this means returning
        a structure of built-in Python datatypes. The exact types that can be
        handled will depend on the render classes you have configured for your API.
        '''
        # Don't use the instance argument here since it is a submission instance
        # if a new submission has been created by calling serializer.save()
        # This method needs to return the LTI Outcome parameters for the response renderer.
        ret = self.validated_data
        # using self.validated_data here implies that the serializer should always
        # be instantiated with the data argument, which is fine for LTI since
        # even read requests are posted with a request body
        if ret['req_type'] == LTIOutcomeXMLParser.TYPE_READ:
            exercise = ret['exercise']
            submitter = ret['submitter']
            summary = UserExerciseSummary(exercise, submitter.user)
            best_submission = summary.get_best_submission()
            if best_submission:
                # LTI score is a decimal value in the range 0.0 - 1.0. The decimal point must be a period.
                if exercise.max_points:
                    ret['score'] = "{:f}".format(min(1, abs(best_submission.grade / exercise.max_points)))
                else:
                    ret['score'] = '1.0'
            else:
                ret['score'] = ''
                # an empty result score should be returned if no grade has been set or it has been deleted

        elif ret['req_type'] == LTIOutcomeXMLParser.TYPE_DELETE:
            # we don't delete any submissions
            ret['code_major'] = LTIOutcomeResponseRenderer.CODE_MAJOR_UNSUPPORTED

        return ret

    def to_internal_value(self, data):
        '''Takes the unvalidated incoming data as input and should return the
        validated data that will be made available as serializer.validated_data.
        The return value will also be passed to the .create() or .update() methods
        if .save() is called on the serializer class.
        If any of the validation fails, then the method should raise
        a serializers.ValidationError(errors).
        '''
        # this runs the default validators for the defined serializer fields
        # it raises serializers.ValidationError if there are errors
        try:
            validated_data = super().to_internal_value(data)
        except serializers.ValidationError as e:
            logger.warning('Validation error in LTI Outcomes request: %s', str(e.detail))
            raise

        if (validated_data['req_type'] == LTIOutcomeXMLParser.TYPE_REPLACE
                and 'score' not in validated_data):
            logger.warning('LTI Outcomes replaceResultRequest did not contain the result score')
            raise serializers.ValidationError({
                'score': [LTIOutcomeXMLParser.TYPE_REPLACE + ' request must include the new result score.']
            })

        # retrieve the exercise and user profile instances
        if 'exercise' not in data or 'submitter' not in data:
            exercise, user_profile = parse_sourced_id(validated_data['sourced_id'])
            if exercise is None or user_profile is None:
                raise serializers.ValidationError({
                    'sourced_id': ['Invalid sourcedId.']
                })
        else:
            exercise = data['exercise']
            user_profile = data['submitter']
        validated_data['exercise'] = exercise
        validated_data['submitter'] = user_profile

        return validated_data
