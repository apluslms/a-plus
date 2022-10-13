import uuid

from django.template import loader
from rest_framework import renderers
from rest_framework import status

from .parsers import LTIOutcomeXMLParser


def validation_errors_to_description(errors):
    # errors is a dict mapping serializer field names to error strings
    l = [] # noqa: E741
    for field_name, errors_list in errors.items():
        l.append(field_name + ': ' + ', '.join(errors_list))
    return '; '.join(l)


class LTIOutcomeResponseRenderer(renderers.BaseRenderer):
    media_type = 'application/xml'
    format = 'xml'
    charset = 'utf-8'

    template_name = 'external_services/lti_outcome_response.xml'

    CODE_MAJOR_SUCCESS = 'success'
    CODE_MAJOR_FAILURE = 'failure'
    CODE_MAJOR_UNSUPPORTED = 'unsupported'
    CODE_MINOR_INVALID_SOURCE_DATA = 'invalidsourcedata'
    # LTI status info codes: IMS General Web Services WSDL Binding Guidelines
    # https://www.imsglobal.org/gws/gwsv1p0/imsgws_wsdlBindv1p0.html#1642084
    # pylint: disable-next=arguments-renamed unused-argument too-many-locals
    def render(self, data, media_type=None, renderer_context=None):

        renderer_context = renderer_context or {}

        success = True
        code_major = data.get('code_major', self.CODE_MAJOR_SUCCESS)
        code_minor = None
        request = renderer_context.get('request')
        response = renderer_context.get('response')
        error_detail = data.get('detail')
        # detail is usually a str or string-like rest_framework.exceptions.ErrorDetail,
        # but for ValidationErros it is a dict mapping serializer field names to error strings.
        # In addition, detail is a list if the exercise does not accept the student's submission.
        # data may also contain some of the normal LTI request data in addition to the error detail
        if isinstance(error_detail, dict):
            error_detail = validation_errors_to_description(error_detail)
        elif isinstance(error_detail, list):
            error_detail = '; '.join(error_detail)

        if error_detail or (response and (response.exception or
                            response.status_code >= status.HTTP_400_BAD_REQUEST)):
            code_major = self.CODE_MAJOR_FAILURE
            success = False
            if response.status_code == status.HTTP_400_BAD_REQUEST:
                # probably validation or parse error
                code_minor = self.CODE_MINOR_INVALID_SOURCE_DATA

        # define the description for the response
        if success:
            operation = data.get('req_type')
            if operation == LTIOutcomeXMLParser.TYPE_REPLACE:
                description = 'Score {} added to sourcedId {}'.format(
                    data.get('score', ''),
                    data.get('sourced_id', '')
                )
            elif operation == LTIOutcomeXMLParser.TYPE_READ:
                description = 'SourcedId {} has the score {}'.format(data.get('sourced_id', ''), data.get('score', ''))
            else:
                description = '{} operation is not supported'.format(operation)
        else:
            description = str(error_detail) if error_detail else 'Operation failed'
            try:
                # In case data does not contain normal LTI request data,
                # try to update the data with the request body data (from the parser).
                # The response XML may then refer to the request message ID, etc.
                if isinstance(request.data, dict):
                    # only set keys to data that do not exist there yet
                    for key, val in request.data.items():
                        data.setdefault(key, val)
            except: # noqa: E722
                pass

        ctx = {
            'msg_id': uuid.uuid4().hex, # new unique id, 32 characters
            'code_major': code_major,
            'code_minor': code_minor,
            'severity': data.get('severity', 'status'),
            'description': description,
            'msg_ref_id': data.get('msgid', ''), # copy msgid from the request
            'operation': data.get('req_type', ''),
            'score': data.get('score', ''),
            'UNSUPPORTED': self.CODE_MAJOR_UNSUPPORTED,
            'SUCCESS': self.CODE_MAJOR_SUCCESS,
            'READ_RESULT': LTIOutcomeXMLParser.TYPE_READ,
        }
        template = loader.get_template(self.template_name)
        return template.render(ctx, request=request)
