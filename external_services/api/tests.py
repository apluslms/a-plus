import datetime
import logging

from django.contrib.auth.models import User
from django.utils.formats import date_format
from django.utils import timezone
import lxml
import oauthlib.oauth1
from rest_framework import status
from rest_framework.test import APITestCase

from course.models import Course, CourseInstance, CourseModule, Enrollment, LearningObjectCategory
from exercise.models import LTIExercise, Submission
from external_services.models import LTIService
from userprofile.models import UserProfile, LTIServiceUser

# disable logging so that the log messages do not clutter the test output
logging.disable(logging.CRITICAL)

class LTIOutcomesBaseTest(APITestCase):
    OUTCOMES_API_URL = '/api/v2/lti-outcomes'

    # XML for a request body
    BASE_OUTCOMES_REQUEST_XML = '''<?xml version="1.0" encoding="UTF-8"?>
<imsx_POXEnvelopeRequest xmlns="http://www.imsglobal.org/services/ltiv1p1/xsd/imsoms_v1p0">
  <imsx_POXHeader>
    <imsx_POXRequestHeaderInfo>
      <imsx_version>V1.0</imsx_version>
      <imsx_messageIdentifier>{msg_id}</imsx_messageIdentifier>
    </imsx_POXRequestHeaderInfo>
  </imsx_POXHeader>
  <imsx_POXBody>
    <{operation}Request>
      <resultRecord>
        <sourcedGUID>
          <sourcedId>{sourced_id}</sourcedId>
        </sourcedGUID>
        {result}
      </resultRecord>
    </{operation}Request>
  </imsx_POXBody>
</imsx_POXEnvelopeRequest>'''

    # replaceResult requests and readResult responses must also include the result
    BASE_RESULT_XML = '''<result>
          <resultScore>
            <language>en</language>
            <textString>{score}</textString>
          </resultScore>
        </result>'''

    BASE_OUTCOMES_RESPONSE_XML = '''<?xml version="1.0" encoding="UTF-8"?>
<imsx_POXEnvelopeResponse xmlns="http://www.imsglobal.org/services/ltiv1p1/xsd/imsoms_v1p0">
  <imsx_POXHeader>
    <imsx_POXResponseHeaderInfo>
      <imsx_version>V1.0</imsx_version>
      <imsx_messageIdentifier>{msg_id}</imsx_messageIdentifier>
      <imsx_statusInfo>
        <imsx_codeMajor>{code_major}</imsx_codeMajor>
        <imsx_severity>{severity}</imsx_severity>
        <imsx_description>{description}</imsx_description>
        <imsx_messageRefIdentifier>{msg_ref_id}</imsx_messageRefIdentifier>
        <imsx_operationRefIdentifier>{operation_ref}</imsx_operationRefIdentifier>
        {extra_status}
      </imsx_statusInfo>
    </imsx_POXResponseHeaderInfo>
  </imsx_POXHeader>
  <imsx_POXBody>
    {body}
  </imsx_POXBody>
</imsx_POXEnvelopeResponse>'''

    # assert method for comparing Outcomes response XML messages
    def assertLTIOutcomesResponseXMLEqual(self, got_xml, expected_xml, ignore_elems=None):
        try:
            got_root = lxml.etree.fromstring(got_xml.encode('utf-8'))
            expected_root = lxml.etree.fromstring(expected_xml.encode('utf-8'))
        except Exception as e:
            self.fail('XML parsing failed: ' + str(e))

        ns = '{http://www.imsglobal.org/services/ltiv1p1/xsd/imsoms_v1p0}'
        for status_elem in ('imsx_codeMajor', 'imsx_severity', 'imsx_description',
                            'imsx_messageRefIdentifier', 'imsx_operationRefIdentifier',
                            'imsx_codeMinor'):
            if ignore_elems and status_elem in ignore_elems:
                continue
            query = '{ns}imsx_POXHeader/{ns}imsx_POXResponseHeaderInfo/{ns}imsx_statusInfo/{ns}{status_elem}'.format(
                ns=ns, status_elem=status_elem)
            expected_val = expected_root.findtext(query)
            got_val = got_root.findtext(query)
            self.assertEqual(got_val, expected_val, status_elem + ' not equal')

        query = '{ns}imsx_POXHeader/{ns}imsx_POXResponseHeaderInfo/{ns}imsx_version'.format(ns=ns)
        exp_version = expected_root.findtext(query)
        got_version = got_root.findtext(query)
        self.assertEqual(got_version, exp_version)

        # random, can not know beforehand
        got_msg_id = got_root.findtext('{ns}imsx_POXHeader/{ns}imsx_POXResponseHeaderInfo/{ns}imsx_messageIdentifier'.format(ns=ns))
        self.assertNotEqual(got_msg_id, None)
        self.assertTrue(len(got_msg_id) > 0)

        query = '{ns}imsx_POXBody'.format(ns=ns)
        exp_body = expected_root.find(query)
        got_body = got_root.find(query)
        # number of children
        self.assertEqual(len(exp_body), len(got_body))
        if len(exp_body):
            self.assertEqual(exp_body[0].tag, got_body[0].tag)
        # only readResultResponses have some real content in the body
        exp_readResult = expected_root.find('{ns}imsx_POXBody/{ns}readResultResponse'.format(ns=ns))
        if exp_readResult is not None:
            query = '{ns}imsx_POXBody/{ns}readResultResponse/{ns}result/{ns}resultScore/{ns}textString'.format(ns=ns)
            exp_score = expected_root.findtext(query)
            got_score = got_root.findtext(query)
            self.assertEqual(got_score, exp_score)

            query = '{ns}imsx_POXBody/{ns}readResultResponse/{ns}result/{ns}resultScore/{ns}language'.format(ns=ns)
            got_lang = got_root.findtext(query)
            self.assertEqual(got_lang, 'en') # specification requires "en"

    def mk_sourced_id(self, lti_exercise, user=None, enrollment=None):
        if enrollment and lti_exercise.lti_service.is_anonymous:
            user_id = 'a' + enrollment.anon_id
        elif user and not lti_exercise.lti_service.is_anonymous:
            user_id = 'i' + str(user.pk)
        else:
            self.fail('mk_sourced_id requires the enrollment argument for anonymous LTI services and user otherwise.')
        return '{}-{}'.format(lti_exercise.pk, user_id)


class LTIOutcomesTests(LTIOutcomesBaseTest):

    @classmethod
    def setUpTestData(cls):
        cls.now = timezone.now()
        cls.year_before = cls.now - datetime.timedelta(days=365)
        cls.year_after = cls.now + datetime.timedelta(days=365)

        cls.student1 = User.objects.create_user(username='student1', password='123456')
        cls.student1_profile = UserProfile.objects.get(user=cls.student1)
        cls.student1_profile.student_id = '123456'
        cls.student1_profile.save()

        cls.lti_service = LTIService.objects.create(
            url='http://localhost:8080/lti-launch', # fake URL
            consumer_key='apluskey',
            consumer_secret='aplussecret',
            access_settings=LTIService.LTI_ACCESS.ANON_API_NO,
        )
        cls.course = Course.objects.create(
            name='Test course',
            code='test',
            url='test',
        )
        cls.course_instance = CourseInstance.objects.create(
            course=cls.course,
            instance_name='Test',
            url='test',
            starting_time=cls.year_before,
            ending_time=cls.year_after,
        )
        cls.student1_enrollment = Enrollment.objects.create(
            course_instance=cls.course_instance,
            user_profile=cls.student1_profile,
        )
        cls.course_module = CourseModule.objects.create(
            name='Module 1',
            url='module1',
            course_instance=cls.course_instance,
            opening_time=cls.year_before,
            closing_time=cls.year_after,
        )
        cls.category = LearningObjectCategory.objects.create(
            name='LTI exercises',
            course_instance=cls.course_instance,
        )
        cls.lti_exercise = LTIExercise.objects.create(
            name='LTI exercise 1',
            category=cls.category,
            course_module=cls.course_module,
            url='ltiex1',
            max_points=100,
            lti_service=cls.lti_service,
        )
        cls.lti_exercise2 = LTIExercise.objects.create(
            name='LTI exercise 2',
            category=cls.category,
            course_module=cls.course_module,
            url='ltiex2',
            max_points=50,
            max_submissions=5,
            lti_service=cls.lti_service,
        )
        cls.lti_user1 = LTIServiceUser(exercise=cls.lti_exercise, lti_service=cls.lti_service, user_id=cls.student1.id)
        cls.lti_user2 = LTIServiceUser(exercise=cls.lti_exercise2, lti_service=cls.lti_service, user_id=cls.student1.id)

    def test_replaceResult(self):
        sourced_id = self.mk_sourced_id(self.lti_exercise, enrollment=self.student1_enrollment)
        req_xml = self.BASE_OUTCOMES_REQUEST_XML.format(
            msg_id='fudyhsgysywe374628mfgu',
            operation='replaceResult',
            sourced_id=sourced_id,
            result=self.BASE_RESULT_XML.format(score='0.71'),
        )

        # OAuth1 signature and body hash for the HTTP request Authorization header
        oauth_client = oauthlib.oauth1.Client(
            client_key=self.lti_service.consumer_key,
            client_secret=self.lti_service.consumer_secret,
            signature_method=oauthlib.oauth1.SIGNATURE_HMAC,
            signature_type=oauthlib.oauth1.SIGNATURE_TYPE_AUTH_HEADER,
        )
        oa_uri, oa_headers, oa_body = oauth_client.sign('http://aplus.local/api/v2/lti-outcomes',
            http_method='POST',
            body=req_xml,
            headers={
                'Content-Type': 'application/xml',
            },
        )

        # make the test request
        response = self.client.post(self.OUTCOMES_API_URL, data=req_xml, content_type='application/xml',
                         HTTP_AUTHORIZATION=oa_headers['Authorization'],
                         SERVER_NAME='aplus.local')
        response_xml = response.content.decode('utf-8')
        root = lxml.etree.fromstring(response_xml.encode('utf-8'))
        response_msg_id = root.findtext('{ns}imsx_POXHeader/{ns}imsx_POXResponseHeaderInfo/{ns}imsx_messageIdentifier'.format(
            ns='{http://www.imsglobal.org/services/ltiv1p1/xsd/imsoms_v1p0}'))

        expected_response_xml = self.BASE_OUTCOMES_RESPONSE_XML.format(
            msg_id=response_msg_id, # random, can not know beforehand
            code_major='success',
            severity='status',
            description='Score {} added to sourcedId {}'.format('0.71', sourced_id),
            msg_ref_id='fudyhsgysywe374628mfgu',
            operation_ref='replaceResult',
            extra_status='',
            body='<replaceResultResponse/>',
        )

        self.maxDiff = None
        self.assertXMLEqual(response_xml, expected_response_xml)

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # find the new submission in the database and check its points
        self.assertEqual(Submission.objects.count(), 1, 'there should be only one submission')
        submission = Submission.objects.first()
        self.assertEqual(submission.grade, 71)
        self.assertEqual(submission.feedback, '')
        self.assertEqual(submission.status, 'ready')
        self.assertEqual(submission.submitters.count(), 1)
        self.assertEqual(submission.submitters.first(), self.student1_profile)
        now = timezone.now()
        self.assertTrue(submission.submission_time < now + datetime.timedelta(minutes=1))
        self.assertTrue(submission.submission_time > now - datetime.timedelta(minutes=1))
        self.assertEqual(submission.grading_data, {
            'score': float('0.71'),
            'lti_msgid': 'fudyhsgysywe374628mfgu',
            'sourced_id': sourced_id,
        })

    def test_readResult(self):
        # create submissions in the database
        sourced_id1 = self.mk_sourced_id(self.lti_exercise, enrollment=self.student1_enrollment)
        submission1 = Submission.objects.create(
            exercise=self.lti_exercise,
            status=Submission.STATUS.READY,
            grade=46,
            grading_time=self.now,
            grading_data={
                'score': '0.46',
                'lti_msgid': 'ifhdye73yjdnhwy',
                'sourced_id': sourced_id1,
            },
        )
        submission1.submitters.set([self.student1_profile])

        # second submission in the same exercise
        sourced_id2 = self.mk_sourced_id(self.lti_exercise, enrollment=self.student1_enrollment)
        submission2 = Submission.objects.create(
            exercise=self.lti_exercise,
            status=Submission.STATUS.READY,
            grade=20,
            grading_time=self.now,
            grading_data={
                'score': '0.20',
                'lti_msgid': 'kfofi8ey7dbndu',
                'sourced_id': sourced_id2,
            },
        )
        submission2.submitters.set([self.student1_profile])

        # different exercise
        sourced_id3 = self.mk_sourced_id(self.lti_exercise2, enrollment=self.student1_enrollment)
        submission3 = Submission.objects.create(
            exercise=self.lti_exercise2,
            status=Submission.STATUS.READY,
            grade=48,
            grading_time=self.now,
            grading_data={
                'score': '0.96',
                'lti_msgid': 'i8463yrfjdbdye63hdksHFisk',
                'sourced_id': sourced_id3,
            },
        )
        submission3.submitters.set([self.student1_profile])

        # make the test request
        req_xml1 = self.BASE_OUTCOMES_REQUEST_XML.format(
            msg_id='84yfhdbwbnwuwe254',
            operation='readResult',
            sourced_id=sourced_id1,
            result='',
        )
        self.client.force_authenticate(user=self.lti_user1) # skip OAuth credentials
        response1 = self.client.post(self.OUTCOMES_API_URL, data=req_xml1, content_type='application/xml')
        response_xml1 = response1.content.decode('utf-8')

        expected_response_xml1 = self.BASE_OUTCOMES_RESPONSE_XML.format(
            msg_id='xxx', # random, can not know beforehand
            code_major='success',
            severity='status',
            description='SourcedId {} has the score {}'.format(sourced_id1, '0.460000'),
            msg_ref_id='84yfhdbwbnwuwe254',
            operation_ref='readResult',
            extra_status='',
            body='<readResultResponse>{}</readResultResponse>'.format(
                self.BASE_RESULT_XML.format(score='0.460000')),
        )
        # compare XML without msg id
        self.assertLTIOutcomesResponseXMLEqual(response_xml1, expected_response_xml1)
        self.assertEqual(response1.status_code, status.HTTP_200_OK)

        # readResult for the second exercise
        req_xml2 = self.BASE_OUTCOMES_REQUEST_XML.format(
            msg_id='jo8367tjhbcjsuiduo4',
            operation='readResult',
            sourced_id=sourced_id3,
            result='',
        )
        self.client.force_authenticate(user=self.lti_user2)
        response2 = self.client.post(self.OUTCOMES_API_URL, data=req_xml2, content_type='application/xml')
        response_xml2 = response2.content.decode('utf-8')

        expected_response_xml2 = self.BASE_OUTCOMES_RESPONSE_XML.format(
            msg_id='xxx', # random, can not know beforehand
            code_major='success',
            severity='status',
            description='SourcedId {} has the score {}'.format(sourced_id3, '0.960000'),
            msg_ref_id='jo8367tjhbcjsuiduo4',
            operation_ref='readResult',
            extra_status='',
            body='<readResultResponse>{}</readResultResponse>'.format(
                self.BASE_RESULT_XML.format(score='0.960000')),
        )
        # compare XML without msg id
        self.assertLTIOutcomesResponseXMLEqual(response_xml2, expected_response_xml2)

    def test_readResult_no_result(self):
        # no submissions exist, readResult score is an empty string
        self.assertEqual(Submission.objects.count(), 0)
        sourced_id1 = self.mk_sourced_id(self.lti_exercise, enrollment=self.student1_enrollment)
        # make the test request
        req_xml1 = self.BASE_OUTCOMES_REQUEST_XML.format(
            msg_id='jdndu36729qoshs63jfs',
            operation='readResult',
            sourced_id=sourced_id1,
            result='',
        )
        self.client.force_authenticate(user=self.lti_user1) # skip OAuth credentials
        response1 = self.client.post(self.OUTCOMES_API_URL, data=req_xml1, content_type='application/xml')
        response_xml1 = response1.content.decode('utf-8')

        expected_response_xml1 = self.BASE_OUTCOMES_RESPONSE_XML.format(
            msg_id='xxx', # random, can not know beforehand
            code_major='success',
            severity='status',
            description='SourcedId {} has the score {}'.format(sourced_id1, ''),
            msg_ref_id='jdndu36729qoshs63jfs',
            operation_ref='readResult',
            extra_status='',
            body='<readResultResponse>{}</readResultResponse>'.format(
                self.BASE_RESULT_XML.format(score='')),
        )
        # compare XML without msg id
        self.assertLTIOutcomesResponseXMLEqual(response_xml1, expected_response_xml1)
        self.assertEqual(response1.status_code, status.HTTP_200_OK)

    def test_deleteResult(self):
        # response states that the deleteResult operation is unsupported and no submission is deleted
        sourced_id1 = self.mk_sourced_id(self.lti_exercise, enrollment=self.student1_enrollment)
        submission1 = Submission.objects.create(
            exercise=self.lti_exercise,
            status=Submission.STATUS.READY,
            grade=86,
            grading_time=self.now,
            grading_data={
                'score': '0.86',
                'lti_msgid': 'khnsdnsdi2743j2',
                'sourced_id': sourced_id1,
            },
        )
        submission1.submitters.set([self.student1_profile])

        # make the test request
        req_xml1 = self.BASE_OUTCOMES_REQUEST_XML.format(
            msg_id='nvldoe837jslsurkg',
            operation='deleteResult',
            sourced_id=sourced_id1,
            result='',
        )
        self.client.force_authenticate(user=self.lti_user1) # skip OAuth credentials
        response1 = self.client.post(self.OUTCOMES_API_URL, data=req_xml1, content_type='application/xml')
        response_xml1 = response1.content.decode('utf-8')

        expected_response_xml1 = self.BASE_OUTCOMES_RESPONSE_XML.format(
            msg_id='xxx', # random, can not know beforehand
            code_major='unsupported',
            severity='status',
            description='deleteResult operation is not supported',
            msg_ref_id='nvldoe837jslsurkg',
            operation_ref='deleteResult',
            extra_status='',
            body='', # empty body when status is unsupported
        )
        # compare XML without msg id
        self.assertLTIOutcomesResponseXMLEqual(response_xml1, expected_response_xml1)
        self.assertEqual(response1.status_code, status.HTTP_200_OK)

        # check that the submission was not deleted
        self.assertEqual(Submission.objects.count(), 1)
        self.assertEqual(Submission.objects.first().pk, submission1.pk)

    def test_replaceResult2(self):
        # make 2 requests and check that there are 2 new submissions
        sourced_id1 = self.mk_sourced_id(self.lti_exercise, enrollment=self.student1_enrollment)
        req_xml1 = self.BASE_OUTCOMES_REQUEST_XML.format(
            msg_id='jnvbcvxsrw538r49ri',
            operation='replaceResult',
            sourced_id=sourced_id1,
            result=self.BASE_RESULT_XML.format(score='0.88'),
        )
        self.client.force_authenticate(user=self.lti_user1) # skip OAuth credentials
        response1 = self.client.post(self.OUTCOMES_API_URL, data=req_xml1, content_type='application/xml')
        response_xml1 = response1.content.decode('utf-8')
        expected_response_xml1 = self.BASE_OUTCOMES_RESPONSE_XML.format(
            msg_id='xxxx', # random, can not know beforehand
            code_major='success',
            severity='status',
            description='Score {} added to sourcedId {}'.format('0.88', sourced_id1),
            msg_ref_id='jnvbcvxsrw538r49ri',
            operation_ref='replaceResult',
            extra_status='',
            body='<replaceResultResponse/>',
        )

        self.assertLTIOutcomesResponseXMLEqual(response_xml1, expected_response_xml1)

        # another replaceResult request
        sourced_id2 = sourced_id1
        req_xml2 = self.BASE_OUTCOMES_REQUEST_XML.format(
            msg_id='cxduedu73tiew7fjdoe',
            operation='replaceResult',
            sourced_id=sourced_id2,
            result=self.BASE_RESULT_XML.format(score='0.26'),
        )
        response2 = self.client.post(self.OUTCOMES_API_URL, data=req_xml2, content_type='application/xml')
        response_xml2 = response2.content.decode('utf-8')
        expected_response_xml2 = self.BASE_OUTCOMES_RESPONSE_XML.format(
            msg_id='xxxx', # random, can not know beforehand
            code_major='success',
            severity='status',
            description='Score {} added to sourcedId {}'.format('0.26', sourced_id2),
            msg_ref_id='cxduedu73tiew7fjdoe',
            operation_ref='replaceResult',
            extra_status='',
            body='<replaceResultResponse/>',
        )

        self.assertLTIOutcomesResponseXMLEqual(response_xml2, expected_response_xml2)
        self.assertEqual(response2.status_code, status.HTTP_200_OK)

        # check the submissions in the database
        self.assertEqual(Submission.objects.count(), 2)
        submission1 = Submission.objects.get(grade=88)
        submission2 = Submission.objects.get(grade=26)
        self.assertEqual(submission1.status, 'ready')
        self.assertEqual(submission2.status, 'ready')
        self.assertEqual(submission1.exercise.pk, self.lti_exercise.pk)
        self.assertEqual(submission2.exercise.pk, self.lti_exercise.pk)

    def test_invalid_req_body_no_msg_id(self):
        # invalid request body XML, no messageIdentifier
        sourced_id1 = self.mk_sourced_id(self.lti_exercise, enrollment=self.student1_enrollment)
        req_xml_no_msgid = '''<?xml version="1.0" encoding="UTF-8"?>
<imsx_POXEnvelopeRequest xmlns="http://www.imsglobal.org/services/ltiv1p1/xsd/imsoms_v1p0">
  <imsx_POXHeader>
    <imsx_POXRequestHeaderInfo>
      <imsx_version>V1.0</imsx_version>
    </imsx_POXRequestHeaderInfo>
  </imsx_POXHeader>
  <imsx_POXBody>
    <{operation}Request>
      <resultRecord>
        <sourcedGUID>
          <sourcedId>{sourced_id}</sourcedId>
        </sourcedGUID>
      </resultRecord>
    </{operation}Request>
  </imsx_POXBody>
</imsx_POXEnvelopeRequest>'''.format(
            operation='readResult',
            sourced_id=sourced_id1,
        )

        self.client.force_authenticate(user=self.lti_user1) # skip OAuth credentials
        response1 = self.client.post(self.OUTCOMES_API_URL, data=req_xml_no_msgid, content_type='application/xml')
        response_xml1 = response1.content.decode('utf-8')
        expected_response_xml1 = self.BASE_OUTCOMES_RESPONSE_XML.format(
            msg_id='xxxx', # random, can not know beforehand
            code_major='failure',
            severity='status',
            description='msgid: This field is required.',
            msg_ref_id='',
            operation_ref='readResult',
            extra_status='<imsx_codeMinor>invalidsourcedata</imsx_codeMinor>',
            body='',
        )

        self.assertLTIOutcomesResponseXMLEqual(response_xml1, expected_response_xml1)
        self.assertEqual(response1.status_code, status.HTTP_400_BAD_REQUEST)

    def test_invalid_req_body_empty_msg_id(self):
        # invalid request body XML, empty messageIdentifier element
        sourced_id1 = self.mk_sourced_id(self.lti_exercise, enrollment=self.student1_enrollment)
        req_xml_empty_msgid = '''<?xml version="1.0" encoding="UTF-8"?>
<imsx_POXEnvelopeRequest xmlns="http://www.imsglobal.org/services/ltiv1p1/xsd/imsoms_v1p0">
  <imsx_POXHeader>
    <imsx_POXRequestHeaderInfo>
      <imsx_version>V1.0</imsx_version>
      <imsx_messageIdentifier></imsx_messageIdentifier>
    </imsx_POXRequestHeaderInfo>
  </imsx_POXHeader>
  <imsx_POXBody>
    <{operation}Request>
      <resultRecord>
        <sourcedGUID>
          <sourcedId>{sourced_id}</sourcedId>
        </sourcedGUID>
      </resultRecord>
    </{operation}Request>
  </imsx_POXBody>
</imsx_POXEnvelopeRequest>'''.format(
            operation='readResult',
            sourced_id=sourced_id1,
        )

        self.client.force_authenticate(user=self.lti_user1) # skip OAuth credentials
        response1 = self.client.post(self.OUTCOMES_API_URL, data=req_xml_empty_msgid, content_type='application/xml')
        response_xml1 = response1.content.decode('utf-8')
        expected_response_xml1 = self.BASE_OUTCOMES_RESPONSE_XML.format(
            msg_id='xxxx', # random, can not know beforehand
            code_major='failure',
            severity='status',
            description='msgid: This field may not be blank.',
            msg_ref_id='',
            operation_ref='readResult',
            extra_status='<imsx_codeMinor>invalidsourcedata</imsx_codeMinor>',
            body='',
        )

        self.assertLTIOutcomesResponseXMLEqual(response_xml1, expected_response_xml1)
        self.assertEqual(response1.status_code, status.HTTP_400_BAD_REQUEST)

    def test_invalid_req_body_no_sourced_id(self):
        # invalid request body XML, no sourcedId element
        req_xml_no_sourced_id = '''<?xml version="1.0" encoding="UTF-8"?>
<imsx_POXEnvelopeRequest xmlns="http://www.imsglobal.org/services/ltiv1p1/xsd/imsoms_v1p0">
  <imsx_POXHeader>
    <imsx_POXRequestHeaderInfo>
      <imsx_version>V1.0</imsx_version>
      <imsx_messageIdentifier>{msgid}</imsx_messageIdentifier>
    </imsx_POXRequestHeaderInfo>
  </imsx_POXHeader>
  <imsx_POXBody>
    <{operation}Request>
      <resultRecord>
      </resultRecord>
    </{operation}Request>
  </imsx_POXBody>
</imsx_POXEnvelopeRequest>'''.format(
            msgid='lghofudgw63yrjfhe6',
            operation='readResult',
        )

        self.client.force_authenticate(user=LTIServiceUser()) # skip OAuth credentials
        response1 = self.client.post(self.OUTCOMES_API_URL, data=req_xml_no_sourced_id, content_type='application/xml')
        response_xml1 = response1.content.decode('utf-8')
        expected_response_xml1 = self.BASE_OUTCOMES_RESPONSE_XML.format(
            msg_id='xxxx', # random, can not know beforehand
            code_major='failure',
            severity='status',
            description='sourced_id: This field is required.',
            msg_ref_id='lghofudgw63yrjfhe6',
            operation_ref='readResult',
            extra_status='<imsx_codeMinor>invalidsourcedata</imsx_codeMinor>',
            body='',
        )

        self.assertLTIOutcomesResponseXMLEqual(response_xml1, expected_response_xml1)
        self.assertEqual(response1.status_code, status.HTTP_400_BAD_REQUEST)

    def test_invalid_req_body_unknown_operation(self):
        # invalid request body XML, operation in the POXBody is unknown
        sourced_id1 = self.mk_sourced_id(self.lti_exercise, enrollment=self.student1_enrollment)
        req_xml_unknown_operation = '''<?xml version="1.0" encoding="UTF-8"?>
<imsx_POXEnvelopeRequest xmlns="http://www.imsglobal.org/services/ltiv1p1/xsd/imsoms_v1p0">
  <imsx_POXHeader>
    <imsx_POXRequestHeaderInfo>
      <imsx_version>V1.0</imsx_version>
      <imsx_messageIdentifier>{msgid}</imsx_messageIdentifier>
    </imsx_POXRequestHeaderInfo>
  </imsx_POXHeader>
  <imsx_POXBody>
    <{operation}Request>
      <resultRecord>
        <sourcedGUID>
          <sourcedId>{sourced_id}</sourcedId>
        </sourcedGUID>
      </resultRecord>
    </{operation}Request>
  </imsx_POXBody>
</imsx_POXEnvelopeRequest>'''.format(
            msgid='cchdujfg836759odjd',
            sourced_id=sourced_id1,
            operation='retrieveResult', # fake operation
        )

        self.client.force_authenticate(user=self.lti_user1) # skip OAuth credentials
        response1 = self.client.post(self.OUTCOMES_API_URL, data=req_xml_unknown_operation, content_type='application/xml')
        response_xml1 = response1.content.decode('utf-8')
        expected_response_xml1 = self.BASE_OUTCOMES_RESPONSE_XML.format(
            msg_id='xxxx', # random, can not know beforehand
            code_major='failure',
            severity='status',
            description='req_type: "retrieveResult" is not a valid choice.',
            msg_ref_id='cchdujfg836759odjd',
            operation_ref='retrieveResult',
            extra_status='<imsx_codeMinor>invalidsourcedata</imsx_codeMinor>',
            body='',
        )

        self.assertLTIOutcomesResponseXMLEqual(response_xml1, expected_response_xml1)
        self.assertEqual(response1.status_code, status.HTTP_400_BAD_REQUEST)

    def test_invalid_req_body_unknown_operation2(self):
        # invalid request body XML, operation in the POXBody is unknown and does not end with "Request"
        sourced_id1 = self.mk_sourced_id(self.lti_exercise, enrollment=self.student1_enrollment)
        req_xml_unknown_operation = '''<?xml version="1.0" encoding="UTF-8"?>
<imsx_POXEnvelopeRequest xmlns="http://www.imsglobal.org/services/ltiv1p1/xsd/imsoms_v1p0">
  <imsx_POXHeader>
    <imsx_POXRequestHeaderInfo>
      <imsx_version>V1.0</imsx_version>
      <imsx_messageIdentifier>{msgid}</imsx_messageIdentifier>
    </imsx_POXRequestHeaderInfo>
  </imsx_POXHeader>
  <imsx_POXBody>
    <foo>
      <resultRecord>
        <sourcedGUID>
          <sourcedId>{sourced_id}</sourcedId>
        </sourcedGUID>
      </resultRecord>
    </foo>
  </imsx_POXBody>
</imsx_POXEnvelopeRequest>'''.format(
            msgid='arwt374ufjhdhne',
            sourced_id=sourced_id1,
        )

        self.client.force_authenticate(user=self.lti_user1) # skip OAuth credentials
        response1 = self.client.post(self.OUTCOMES_API_URL, data=req_xml_unknown_operation, content_type='application/xml')
        response_xml1 = response1.content.decode('utf-8')
        expected_response_xml1 = self.BASE_OUTCOMES_RESPONSE_XML.format(
            msg_id='xxxx', # random, can not know beforehand
            code_major='failure',
            severity='status',
            description='req_type: "" is not a valid choice.',
            msg_ref_id='arwt374ufjhdhne',
            operation_ref='', # the parser truncates the "foo" element name to the empty string
            extra_status='<imsx_codeMinor>invalidsourcedata</imsx_codeMinor>',
            body='',
        )

        self.assertLTIOutcomesResponseXMLEqual(response_xml1, expected_response_xml1)
        self.assertEqual(response1.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(Submission.objects.count(), 0)

    def test_invalid_req_body_no_score_in_replace(self):
        # invalid request body XML, replaceResultRequest with an empty score
        sourced_id1 = self.mk_sourced_id(self.lti_exercise, enrollment=self.student1_enrollment)
        req_xml_no_score = '''<?xml version="1.0" encoding="UTF-8"?>
<imsx_POXEnvelopeRequest xmlns="http://www.imsglobal.org/services/ltiv1p1/xsd/imsoms_v1p0">
  <imsx_POXHeader>
    <imsx_POXRequestHeaderInfo>
      <imsx_version>V1.0</imsx_version>
      <imsx_messageIdentifier>{msgid}</imsx_messageIdentifier>
    </imsx_POXRequestHeaderInfo>
  </imsx_POXHeader>
  <imsx_POXBody>
    <{operation}Request>
      <resultRecord>
        <sourcedGUID>
          <sourcedId>{sourced_id}</sourcedId>
        </sourcedGUID>
        <result>
          <resultScore>
            <language>en</language>
            <textString></textString>
          </resultScore>
        </result>
      </resultRecord>
    </{operation}Request>
  </imsx_POXBody>
</imsx_POXEnvelopeRequest>'''.format(
            msgid='xhfgd836togjsus7g',
            operation='replaceResult',
            sourced_id=sourced_id1,
        )

        self.client.force_authenticate(user=self.lti_user1) # skip OAuth credentials
        response1 = self.client.post(self.OUTCOMES_API_URL, data=req_xml_no_score, content_type='application/xml')
        response_xml1 = response1.content.decode('utf-8')
        expected_response_xml1 = self.BASE_OUTCOMES_RESPONSE_XML.format(
            msg_id='xxxx', # random, can not know beforehand
            code_major='failure',
            severity='status',
            description='score: A valid number is required.',
            msg_ref_id='xhfgd836togjsus7g',
            operation_ref='replaceResult',
            extra_status='<imsx_codeMinor>invalidsourcedata</imsx_codeMinor>',
            body='',
        )

        self.assertLTIOutcomesResponseXMLEqual(response_xml1, expected_response_xml1)
        self.assertEqual(response1.status_code, status.HTTP_400_BAD_REQUEST)
        # no submission was created
        self.assertEqual(Submission.objects.count(), 0)

    def test_invalid_req_body_no_score_in_replace2(self):
        # invalid request body XML, replaceResultRequest with no score element
        sourced_id1 = self.mk_sourced_id(self.lti_exercise, enrollment=self.student1_enrollment)
        req_xml_no_score = '''<?xml version="1.0" encoding="UTF-8"?>
<imsx_POXEnvelopeRequest xmlns="http://www.imsglobal.org/services/ltiv1p1/xsd/imsoms_v1p0">
  <imsx_POXHeader>
    <imsx_POXRequestHeaderInfo>
      <imsx_version>V1.0</imsx_version>
      <imsx_messageIdentifier>{msgid}</imsx_messageIdentifier>
    </imsx_POXRequestHeaderInfo>
  </imsx_POXHeader>
  <imsx_POXBody>
    <{operation}Request>
      <resultRecord>
        <sourcedGUID>
          <sourcedId>{sourced_id}</sourcedId>
        </sourcedGUID>
        <result>
          <resultScore>
            <language>en</language>
          </resultScore>
        </result>
      </resultRecord>
    </{operation}Request>
  </imsx_POXBody>
</imsx_POXEnvelopeRequest>'''.format(
            msgid='ogifhu7w3634hdhd',
            operation='replaceResult',
            sourced_id=sourced_id1,
        )

        self.client.force_authenticate(user=self.lti_user1) # skip OAuth credentials
        response1 = self.client.post(self.OUTCOMES_API_URL, data=req_xml_no_score, content_type='application/xml')
        response_xml1 = response1.content.decode('utf-8')
        expected_response_xml1 = self.BASE_OUTCOMES_RESPONSE_XML.format(
            msg_id='xxxx', # random, can not know beforehand
            code_major='failure',
            severity='status',
            description='score: replaceResult request must include the new result score.',
            msg_ref_id='ogifhu7w3634hdhd',
            operation_ref='replaceResult',
            extra_status='<imsx_codeMinor>invalidsourcedata</imsx_codeMinor>',
            body='',
        )

        self.assertLTIOutcomesResponseXMLEqual(response_xml1, expected_response_xml1)
        self.assertEqual(response1.status_code, status.HTTP_400_BAD_REQUEST)
        # no submission was created
        self.assertEqual(Submission.objects.count(), 0)

    def test_invalid_req_body_bad_score(self):
        # invalid request body XML, replaceResultRequest with a score over 1
        sourced_id1 = self.mk_sourced_id(self.lti_exercise, enrollment=self.student1_enrollment)
        req_xml_no_score = '''<?xml version="1.0" encoding="UTF-8"?>
<imsx_POXEnvelopeRequest xmlns="http://www.imsglobal.org/services/ltiv1p1/xsd/imsoms_v1p0">
  <imsx_POXHeader>
    <imsx_POXRequestHeaderInfo>
      <imsx_version>V1.0</imsx_version>
      <imsx_messageIdentifier>{msgid}</imsx_messageIdentifier>
    </imsx_POXRequestHeaderInfo>
  </imsx_POXHeader>
  <imsx_POXBody>
    <{operation}Request>
      <resultRecord>
        <sourcedGUID>
          <sourcedId>{sourced_id}</sourcedId>
        </sourcedGUID>
        <result>
          <resultScore>
            <language>en</language>
            <textString>{score}</textString>
          </resultScore>
        </result>
      </resultRecord>
    </{operation}Request>
  </imsx_POXBody>
</imsx_POXEnvelopeRequest>'''.format(
            msgid='cjfud7374uytiodpfie',
            operation='replaceResult',
            sourced_id=sourced_id1,
            score='1.01',
        )

        self.client.force_authenticate(user=self.lti_user1) # skip OAuth credentials
        response1 = self.client.post(self.OUTCOMES_API_URL, data=req_xml_no_score, content_type='application/xml')
        response_xml1 = response1.content.decode('utf-8')
        expected_response_xml1 = self.BASE_OUTCOMES_RESPONSE_XML.format(
            msg_id='xxxx', # random, can not know beforehand
            code_major='failure',
            severity='status',
            description='score: Ensure this value is less than or equal to 1.',
            msg_ref_id='cjfud7374uytiodpfie',
            operation_ref='replaceResult',
            extra_status='<imsx_codeMinor>invalidsourcedata</imsx_codeMinor>',
            body='',
        )

        self.assertLTIOutcomesResponseXMLEqual(response_xml1, expected_response_xml1)
        self.assertEqual(response1.status_code, status.HTTP_400_BAD_REQUEST)
        # no submission was created
        self.assertEqual(Submission.objects.count(), 0)

    def test_invalid_oauth_req(self):
        # request has bad OAuth parameters and authentication fails
        sourced_id = self.mk_sourced_id(self.lti_exercise, enrollment=self.student1_enrollment)
        req_xml = self.BASE_OUTCOMES_REQUEST_XML.format(
            msg_id='poubchsd7w63',
            operation='replaceResult',
            sourced_id=sourced_id,
            result=self.BASE_RESULT_XML.format(score='0.92'),
        )

        # OAuth1 signature and body hash for the HTTP request Authorization header
        oauth_client = oauthlib.oauth1.Client(
            client_key=self.lti_service.consumer_key,
            client_secret='thewrongsecret',
            signature_method=oauthlib.oauth1.SIGNATURE_HMAC,
            signature_type=oauthlib.oauth1.SIGNATURE_TYPE_AUTH_HEADER,
        )
        oa_uri, oa_headers, oa_body = oauth_client.sign('http://aplus.local/api/v2/lti-outcomes',
            http_method='POST',
            body=req_xml,
            headers={
                'Content-Type': 'application/xml',
            },
        )

        # make the test request
        response = self.client.post(self.OUTCOMES_API_URL, data=req_xml, content_type='application/xml',
                         HTTP_AUTHORIZATION=oa_headers['Authorization'],
                         SERVER_NAME='aplus.local')
        response_xml = response.content.decode('utf-8')

        expected_response_xml = self.BASE_OUTCOMES_RESPONSE_XML.format(
            msg_id='xxxxx', # random, can not know beforehand
            code_major='failure',
            severity='status',
            description='OAuth verification failed: oauth_signature verification failed',
            msg_ref_id='poubchsd7w63',
            operation_ref='replaceResult',
            extra_status='',
            body='',
        )

        self.assertLTIOutcomesResponseXMLEqual(response_xml, expected_response_xml)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

        # check that no submission was made
        self.assertEqual(Submission.objects.count(), 0)

    def test_invalid_oauth_and_XML(self):
        # OAuth credentials are invalid and the body XML causes ParseError
        req_xml = '''<?xml version="1.0" encoding="UTF-8"?>
<imsx_POXEnvelopeRequest xmlns="http://www.imsglobal.org/services/ltiv1p1/xsd/imsoms_v1p0">'''

        # OAuth1 signature and body hash for the HTTP request Authorization header
        oauth_client = oauthlib.oauth1.Client(
            client_key=self.lti_service.consumer_key,
            client_secret='thewrongsecret',
            signature_method=oauthlib.oauth1.SIGNATURE_HMAC,
            signature_type=oauthlib.oauth1.SIGNATURE_TYPE_AUTH_HEADER,
        )
        oa_uri, oa_headers, oa_body = oauth_client.sign('http://aplus.local/api/v2/lti-outcomes',
            http_method='POST',
            body=req_xml,
            headers={
                'Content-Type': 'application/xml',
            },
        )

        # make the test request
        response = self.client.post(self.OUTCOMES_API_URL, data=req_xml, content_type='application/xml',
                         HTTP_AUTHORIZATION=oa_headers['Authorization'],
                         SERVER_NAME='aplus.local')
        response_xml = response.content.decode('utf-8')

        expected_response_xml = self.BASE_OUTCOMES_RESPONSE_XML.format(
            msg_id='xxxxx', # random, can not know beforehand
            code_major='failure',
            severity='status',
            description='THIS FIELD IS NOT VALIDATED',
            msg_ref_id='',
            operation_ref='',
            extra_status='<imsx_codeMinor>invalidsourcedata</imsx_codeMinor>',
            body='',
        )

        self.assertLTIOutcomesResponseXMLEqual(
            response_xml,
            expected_response_xml,
            ignore_elems={'imsx_description'},
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        # check that no submission was made
        self.assertEqual(Submission.objects.count(), 0)

    def test_no_auth_header(self):
        # no HTTP Authorization header in the request, auth fails
        sourced_id = self.mk_sourced_id(self.lti_exercise, enrollment=self.student1_enrollment)
        req_xml = self.BASE_OUTCOMES_REQUEST_XML.format(
            msg_id='lofide7364ghdhsu',
            operation='replaceResult',
            sourced_id=sourced_id,
            result=self.BASE_RESULT_XML.format(score='0.64'),
        )

        # make the test request
        response = self.client.post(self.OUTCOMES_API_URL, data=req_xml, content_type='application/xml',
                         SERVER_NAME='aplus.local')
        response_xml = response.content.decode('utf-8')

        expected_response_xml = self.BASE_OUTCOMES_RESPONSE_XML.format(
            msg_id='xxxxx', # random, can not know beforehand
            code_major='failure',
            severity='status',
            description='Authentication credentials were not provided.',
            msg_ref_id='lofide7364ghdhsu',
            operation_ref='replaceResult',
            extra_status='',
            body='',
        )

        self.assertLTIOutcomesResponseXMLEqual(response_xml, expected_response_xml)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        # check that no submission was made
        self.assertEqual(Submission.objects.count(), 0)

    def test_nonce_reuse(self):
        # reuse the same nonce another time, authentication should fail
        sourced_id = self.mk_sourced_id(self.lti_exercise, enrollment=self.student1_enrollment)
        req_xml = self.BASE_OUTCOMES_REQUEST_XML.format(
            msg_id='hvudfud7e63y',
            operation='replaceResult',
            sourced_id=sourced_id,
            result=self.BASE_RESULT_XML.format(score='0.64'),
        )

        # OAuth1 signature and body hash for the HTTP request Authorization header
        oauth_client = oauthlib.oauth1.Client(
            client_key=self.lti_service.consumer_key,
            client_secret=self.lti_service.consumer_secret,
            signature_method=oauthlib.oauth1.SIGNATURE_HMAC,
            signature_type=oauthlib.oauth1.SIGNATURE_TYPE_AUTH_HEADER,
        )
        oa_uri, oa_headers, oa_body = oauth_client.sign('http://aplus.local' + self.OUTCOMES_API_URL,
            http_method='POST',
            body=req_xml,
            headers={
                'Content-Type': 'application/xml',
            },
        )

        # make the test request
        response = self.client.post(self.OUTCOMES_API_URL, data=req_xml, content_type='application/xml',
                HTTP_AUTHORIZATION=oa_headers['Authorization'],
                SERVER_NAME='aplus.local')
        response_xml = response.content.decode('utf-8')

        expected_response_xml = self.BASE_OUTCOMES_RESPONSE_XML.format(
            msg_id='xxxxx', # random, can not know beforehand
            code_major='success',
            severity='status',
            description='Score {} added to sourcedId {}'.format('0.64', sourced_id),
            msg_ref_id='hvudfud7e63y',
            operation_ref='replaceResult',
            extra_status='',
            body='<replaceResultResponse/>',
        )

        self.assertLTIOutcomesResponseXMLEqual(response_xml, expected_response_xml)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(Submission.objects.count(), 1)

        # send the same request again, the nonce check should fail
        response2 = self.client.post(self.OUTCOMES_API_URL, data=req_xml, content_type='application/xml',
                HTTP_AUTHORIZATION=oa_headers['Authorization'],
                SERVER_NAME='aplus.local')
        response_xml2 = response2.content.decode('utf-8')

        expected_response_xml2 = self.BASE_OUTCOMES_RESPONSE_XML.format(
            msg_id='xxxxx', # random, can not know beforehand
            code_major='failure',
            severity='status',
            description='OAuth verification failed: oauth_nonce has been used',
            msg_ref_id='hvudfud7e63y',
            operation_ref='replaceResult',
            extra_status='',
            body='',
        )

        self.assertLTIOutcomesResponseXMLEqual(response_xml2, expected_response_xml2)
        self.assertEqual(response2.status_code, status.HTTP_403_FORBIDDEN)
        # no second submission was created
        self.assertEqual(Submission.objects.count(), 1)

    def test_invalid_req_XML(self):
        # LTI XML parser raises ParseError, wrong root element
        req_xml = '''<?xml version="1.0" encoding="UTF-8"?>
<POXEnvelopeRequest xmlns="http://www.imsglobal.org/services/ltiv1p1/xsd/imsoms_v1p0">
  <imsx_POXHeader>
    <imsx_POXRequestHeaderInfo>
      <imsx_version>V1.0</imsx_version>
      <imsx_messageIdentifier>jgjfud73746373ydh</imsx_messageIdentifier>
    </imsx_POXRequestHeaderInfo>
  </imsx_POXHeader>
</POXEnvelopeRequest>'''

        # make the test request
        self.client.force_authenticate(user=LTIServiceUser())
        response = self.client.post(self.OUTCOMES_API_URL, data=req_xml, content_type='application/xml')
        response_xml = response.content.decode('utf-8')

        expected_response_xml = self.BASE_OUTCOMES_RESPONSE_XML.format(
            msg_id='xxxxx', # random, can not know beforehand
            code_major='failure',
            severity='status',
            description='The XML root element is not "{http://www.imsglobal.org/services/ltiv1p1/xsd/imsoms_v1p0}imsx_POXEnvelopeRequest"',
            msg_ref_id='',
            operation_ref='',
            extra_status='<imsx_codeMinor>invalidsourcedata</imsx_codeMinor>',
            body='',
        )

        self.assertLTIOutcomesResponseXMLEqual(response_xml, expected_response_xml)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        # check that no submission was made
        self.assertEqual(Submission.objects.count(), 0)

    def test_exceed_submission_limit(self):
        # student submits too many times. The exercise has limited the max submissions.
        # create the max number of submissions
        for _ in range(self.lti_exercise2.max_submissions):
            submission = Submission.objects.create(
                exercise=self.lti_exercise2,
                status=Submission.STATUS.READY,
                grade=40,
            )
            submission.submitters.set([self.student1_profile])

        # try to make a new submission
        sourced_id1 = self.mk_sourced_id(self.lti_exercise2, enrollment=self.student1_enrollment)
        req_xml1 = self.BASE_OUTCOMES_REQUEST_XML.format(
            msg_id='sawye8fjvjfie734',
            operation='replaceResult',
            sourced_id=sourced_id1,
            result=self.BASE_RESULT_XML.format(score='0.95'),
        )

        self.client.force_authenticate(user=self.lti_user2) # skip OAuth credentials
        response1 = self.client.post(self.OUTCOMES_API_URL, data=req_xml1, content_type='application/xml')
        response_xml1 = response1.content.decode('utf-8')
        expected_response_xml1 = self.BASE_OUTCOMES_RESPONSE_XML.format(
            msg_id='xxxx', # random, can not know beforehand
            code_major='failure',
            severity='status',
            description='You have used the allowed amount of submissions for this assignment.',
            msg_ref_id='sawye8fjvjfie734',
            operation_ref='replaceResult',
            extra_status='',
            body='',
        )

        self.assertLTIOutcomesResponseXMLEqual(response_xml1, expected_response_xml1)
        self.assertEqual(response1.status_code, status.HTTP_200_OK)
        self.assertEqual(Submission.objects.count(), self.lti_exercise2.max_submissions)


class LTIOutcomesNoEnrollmentTests(LTIOutcomesBaseTest):

    @classmethod
    def setUpTestData(cls):
        cls.now = timezone.now()
        cls.year_before = cls.now - datetime.timedelta(days=365)
        cls.year_after = cls.now + datetime.timedelta(days=365)

        cls.student1 = User.objects.create_user(username='student1', password='123456')
        cls.student1_profile = UserProfile.objects.get(user=cls.student1)
        cls.student1_profile.student_id = '123456'
        cls.student1_profile.save()

        cls.lti_service = LTIService.objects.create(
            url='http://localhost:8080/lti-launch', # fake URL
            consumer_key='apluskey',
            consumer_secret='aplussecret',
            access_settings=LTIService.LTI_ACCESS.ANON_API_NO,
        )
        cls.course = Course.objects.create(
            name='Test course',
            code='test',
            url='test',
        )
        cls.course_instance = CourseInstance.objects.create(
            course=cls.course,
            instance_name='Test',
            url='test',
            starting_time=cls.year_before,
            ending_time=cls.year_after,
        )

        cls.category = LearningObjectCategory.objects.create(
            name='LTI exercises',
            course_instance=cls.course_instance,
        )

    def test_replaceResult_without_enrollment(self):
        course_module = CourseModule.objects.create(
            name='Module 1',
            url='module1',
            course_instance=self.course_instance,
            opening_time=self.year_before,
            closing_time=self.year_after,
        )
        lti_exercise = LTIExercise.objects.create(
            name='LTI exercise 1',
            category=self.category,
            course_module=course_module,
            url='ltiex1',
            max_points=50,
            max_submissions=5,
            lti_service=self.lti_service,
        )

        # try to make a new submission
        sourced_id1 = '{}-{}'.format(lti_exercise.pk, 'ahdjdue73yrhdhsdy6we6') # fake sourced id since there is no enrollment
        req_xml1 = self.BASE_OUTCOMES_REQUEST_XML.format(
            msg_id='zjdudu7w6784hthr',
            operation='replaceResult',
            sourced_id=sourced_id1,
            result=self.BASE_RESULT_XML.format(score='0.76'),
        )

        self.client.force_authenticate(user=LTIServiceUser(exercise=lti_exercise, lti_service=self.lti_service)) # skip OAuth credentials
        # authentication would also require a valid sourced id value, but authentication is skipped now
        response1 = self.client.post(self.OUTCOMES_API_URL, data=req_xml1, content_type='application/xml')
        response_xml1 = response1.content.decode('utf-8')
        expected_response_xml1 = self.BASE_OUTCOMES_RESPONSE_XML.format(
            msg_id='xxxx', # random, can not know beforehand
            code_major='failure',
            severity='status',
            description='sourced_id: Invalid sourcedId.',
            msg_ref_id='zjdudu7w6784hthr',
            operation_ref='replaceResult',
            extra_status='<imsx_codeMinor>invalidsourcedata</imsx_codeMinor>',
            body='',
        )

        self.assertLTIOutcomesResponseXMLEqual(response_xml1, expected_response_xml1)
        self.assertEqual(response1.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(Submission.objects.count(), 0)

    def test_replaceResult_after_deadline(self):
        student1_enrollment = Enrollment.objects.create(
            course_instance=self.course_instance,
            user_profile=self.student1_profile,
        )
        course_module = CourseModule.objects.create(
            name='Module 1',
            url='module1',
            course_instance=self.course_instance,
            opening_time=self.year_before,
            closing_time=self.now - datetime.timedelta(days=1), # deadline has passed
        )
        lti_exercise = LTIExercise.objects.create(
            name='LTI exercise 1',
            category=self.category,
            course_module=course_module,
            url='ltiex1',
            max_points=50,
            max_submissions=5,
            lti_service=self.lti_service,
        )

        # try to make a new submission
        sourced_id1 = self.mk_sourced_id(lti_exercise, enrollment=student1_enrollment)
        req_xml1 = self.BASE_OUTCOMES_REQUEST_XML.format(
            msg_id='vbxhsgsy764y3dg',
            operation='replaceResult',
            sourced_id=sourced_id1,
            result=self.BASE_RESULT_XML.format(score='0.76'),
        )

        self.client.force_authenticate(user=LTIServiceUser(exercise=lti_exercise,
                                                           lti_service=self.lti_service,
                                                           user_id=self.student1.id)) # skip OAuth credentials
        response1 = self.client.post(self.OUTCOMES_API_URL, data=req_xml1, content_type='application/xml')
        response_xml1 = response1.content.decode('utf-8')
        expected_response_xml1 = self.BASE_OUTCOMES_RESPONSE_XML.format(
            msg_id='xxxx', # random, can not know beforehand
            code_major='failure',
            severity='status',
            description='The deadline for the assignment has passed ({date}).'.format(
                date=date_format(timezone.localtime(course_module.closing_time), "DATETIME_FORMAT")),
            msg_ref_id='vbxhsgsy764y3dg',
            operation_ref='replaceResult',
            extra_status='',
            body='',
        )

        self.assertLTIOutcomesResponseXMLEqual(response_xml1, expected_response_xml1)
        self.assertEqual(response1.status_code, status.HTTP_200_OK)
        self.assertEqual(Submission.objects.count(), 0)


class LTIOutcomesPublicServiceTests(LTIOutcomesBaseTest):

    @classmethod
    def setUpTestData(cls):
        cls.now = timezone.now()
        cls.year_before = cls.now - datetime.timedelta(days=365)
        cls.year_after = cls.now + datetime.timedelta(days=365)

        cls.student1 = User.objects.create_user(username='student1', password='123456')
        cls.student1_profile = UserProfile.objects.get(user=cls.student1)
        cls.student1_profile.student_id = '123456'
        cls.student1_profile.save()

        cls.lti_service = LTIService.objects.create(
            url='http://localhost:8080/lti-launch', # fake URL
            consumer_key='apluskey',
            consumer_secret='aplussecret',
            access_settings=LTIService.LTI_ACCESS.PUBLIC_API_NO,
        )
        cls.course = Course.objects.create(
            name='Test course',
            code='test',
            url='test',
        )
        cls.course_instance = CourseInstance.objects.create(
            course=cls.course,
            instance_name='Test',
            url='test',
            starting_time=cls.year_before,
            ending_time=cls.year_after,
        )
        cls.student1_enrollment = Enrollment.objects.create(
            course_instance=cls.course_instance,
            user_profile=cls.student1_profile,
        )
        cls.course_module = CourseModule.objects.create(
            name='Module 1',
            url='module1',
            course_instance=cls.course_instance,
            opening_time=cls.now,
            closing_time=cls.year_after,
        )
        cls.category = LearningObjectCategory.objects.create(
            name='LTI exercises',
            course_instance=cls.course_instance,
        )
        cls.lti_exercise = LTIExercise.objects.create(
            name='LTI exercise 1',
            category=cls.category,
            course_module=cls.course_module,
            url='ltiex1',
            max_points=100,
            lti_service=cls.lti_service,
        )
        cls.lti_exercise2 = LTIExercise.objects.create(
            name='LTI exercise 2',
            category=cls.category,
            course_module=cls.course_module,
            url='ltiex2',
            max_points=50,
            max_submissions=5,
            lti_service=cls.lti_service,
        )

    def test_public_service_sourced_id(self):
        # make a replaceResult request
        sourced_id1 = self.mk_sourced_id(self.lti_exercise, user=self.student1)
        req_xml1 = self.BASE_OUTCOMES_REQUEST_XML.format(
            msg_id='nbkif7e6whdhdujd',
            operation='replaceResult',
            sourced_id=sourced_id1,
            result=self.BASE_RESULT_XML.format(score='0.35'),
        )
        self.client.force_authenticate(user=LTIServiceUser(exercise=self.lti_exercise,
                                                           lti_service=self.lti_service,
                                                           user_id=self.student1.id)) # skip OAuth credentials
        response1 = self.client.post(self.OUTCOMES_API_URL, data=req_xml1, content_type='application/xml')
        response_xml1 = response1.content.decode('utf-8')
        expected_response_xml1 = self.BASE_OUTCOMES_RESPONSE_XML.format(
            msg_id='xxxx', # random, can not know beforehand
            code_major='success',
            severity='status',
            description='Score {} added to sourcedId {}'.format('0.35', sourced_id1),
            msg_ref_id='nbkif7e6whdhdujd',
            operation_ref='replaceResult',
            extra_status='',
            body='<replaceResultResponse/>',
        )

        self.assertLTIOutcomesResponseXMLEqual(response_xml1, expected_response_xml1)

        # check the submissions in the database
        self.assertEqual(Submission.objects.count(), 1)
        submission1 = Submission.objects.first()
        self.assertEqual(submission1.status, 'ready')
        self.assertEqual(submission1.exercise.pk, self.lti_exercise.pk)
