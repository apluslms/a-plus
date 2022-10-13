from rest_framework.response import Response
from rest_framework import status
from rest_framework.views import APIView

from .authentication import OAuthBodyHashAuthentication
from .parsers import LTIOutcomeXMLParser
from .renderers import LTIOutcomeResponseRenderer
from .serializers import LTIOutcomeSerializer
from userprofile.permissions import IsLTIServiceUser


class LTIExerciseBasicOutcomesView(APIView):
    '''View that responds to LTI 1.1 Basic Outcomes Service requests that
    are posted by the Tool Provider to A+ in order to return the scores of submissions.
    '''

    parser_classes = (LTIOutcomeXMLParser,)
    authentication_classes = (OAuthBodyHashAuthentication,)
    permission_classes = (IsLTIServiceUser,)
    renderer_classes = (LTIOutcomeResponseRenderer,)
    # pylint: disable-next=unused-argument
    def post(self, request, version=None): # version is the API version parameter from the URL
        # request.data is the parsed Outcome XML in the request body
        serializer = LTIOutcomeSerializer(data=request.data)
        if serializer.is_valid():
            if serializer.validated_data['req_type'] == LTIOutcomeXMLParser.TYPE_REPLACE:
                exercise = serializer.validated_data['exercise']
                student = serializer.validated_data['submitter']
                sbms_status, errors, _students = exercise.check_submission_allowed(student)
                if sbms_status != exercise.SUBMIT_STATUS.ALLOWED:
                    return Response({'detail': errors}, status=status.HTTP_200_OK)
                    # the key "detail" is also used by raised exceptions in authentication and parsing
                serializer.save() # creates a new submission
            return Response(serializer.data, status=status.HTTP_200_OK)

        # Invalid data
        # Validation errors are given in a dict that has field names as keys and
        # the error strings as values.
        # That is confusing since it looks similar to a dict of validated data.
        # We use the key "detail" here to signal an error state to the renderer since
        # the same key is used by authentication and parsing errors.
        return Response({'detail': serializer.errors}, status=status.HTTP_400_BAD_REQUEST)
