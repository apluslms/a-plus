import base64
import hashlib
from io import BytesIO
import logging

from django.contrib.auth.models import User # pylint: disable=imported-auth-user
from rest_framework.parsers import BaseParser
from rest_framework.exceptions import ParseError
from lxml import etree

from course.models import Enrollment
from exercise.exercise_models import LTIExercise


logger = logging.getLogger('aplus.external_services.api')


def parse_sourced_id(sourced_id_str):
    '''Parse a sourcedId value from an LTI 1.1 Outcomes Service request.
    Return a tuple (exercise, user_profile). Either value may be None if
    the instance is not found in the database.
    '''
    exercise_id, _, user_token = sourced_id_str.partition('-')
    if not exercise_id or not user_token:
        return (None, None)

    try:
        exercise = LTIExercise.objects.get(pk=exercise_id)
    except LTIExercise.DoesNotExist:
        exercise = None

    token_type, token = user_token[0], user_token[1:]
    if token_type == 'i':
        try:
            user_profile = User.objects.get(pk=token).userprofile
        except User.DoesNotExist:
            user_profile = None
    elif token_type == 'a':
        try:
            user_profile = Enrollment.objects.get(anon_id=token).user_profile
        except Enrollment.DoesNotExist:
            user_profile = None
    else:
        user_profile = None
    return (exercise, user_profile)


class LTIOutcomeXMLParser(BaseParser):
    """Parser for LTI 1.1 Basic Outcomes Service messages.
    The external service posts these messages to A+ in order to return the score
    of a learner's submission.
    """

    media_type = 'application/xml'

    NS = '{http://www.imsglobal.org/services/ltiv1p1/xsd/imsoms_v1p0}' # namespace in the LTI XML messages

    # LTI 1.1 Basic Outcomes Service operations
    TYPE_READ = 'readResult'
    TYPE_REPLACE = 'replaceResult'
    TYPE_DELETE = 'deleteResult'

    def parse(self, stream, media_type=None, parser_context=None):
        def set_key(data, key, value):
            # do not set None values to the data
            # the XML API returns None if the query finds nothing
            if value is not None:
                data[key] = value

        # the stream can be read only once, but we need to both compute
        # the hash of the data and parse the data as XML
        body_bytes = stream.read()
        # b64encode returns a byte string so it is decoded to a normal string
        body_hash = base64.b64encode(hashlib.sha1(body_bytes).digest()).decode('ASCII')
        stream = BytesIO(body_bytes) # a new file-like object with the same data

        try:
            tree = etree.parse(stream) # pylint: disable=c-extension-no-member
        except etree.XMLSyntaxError as e: # pylint: disable=c-extension-no-member
            logger.warning('XML syntax error in LTI Outcomes request: %s', str(e))
            raise ParseError(str(e)) from e

        root = tree.getroot()
        if root.tag != '{ns}imsx_POXEnvelopeRequest'.format(ns=self.NS):
            logger.warning('Unexpected root element in LTI Outcomes request: %s', root.tag)
            raise ParseError('The XML root element is not "{ns}imsx_POXEnvelopeRequest"'.format(ns=self.NS))

        data = {}
        set_key(data, 'body_hash', body_hash)
        set_key(data, 'version',
            root.findtext('{ns}imsx_POXHeader/{ns}imsx_POXRequestHeaderInfo/{ns}imsx_version'.format(ns=self.NS)))
        set_key(data, 'msgid',
            root.findtext(
                '{ns}imsx_POXHeader/{ns}imsx_POXRequestHeaderInfo/{ns}imsx_messageIdentifier'.format(ns=self.NS)
            ))

        body_elem = root.find('{ns}imsx_POXBody'.format(ns=self.NS))
        if body_elem is not None and len(body_elem):
            # body element exists and has children
            # only one child is expected
            operation_elem = body_elem[0]
            # expecting a known request type, like readResultRequest
            # (three types given in the constants in this class)
            # remove the namespace prefix from the start of the tag name and
            # the suffix "Request" from the end of the tag name
            req_type = operation_elem.tag[len(self.NS):-7]
            data['req_type'] = req_type
            set_key(data, 'sourced_id',
                operation_elem.findtext('{ns}resultRecord/{ns}sourcedGUID/{ns}sourcedId'.format(ns=self.NS)))
            if req_type == self.TYPE_REPLACE:
                set_key(data, 'score',
                    operation_elem.findtext(
                        '{ns}resultRecord/{ns}result/{ns}resultScore/{ns}textString'.format(ns=self.NS)
                    ))

        return data
