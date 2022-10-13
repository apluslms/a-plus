from urllib.parse import quote

from django.contrib.auth.models import User # pylint: disable=imported-auth-user
from django.urls import reverse
from django.test import TestCase, modify_settings, override_settings

from shibboleth_login.parser import shib_join


DEF_SHIBD_META = {
    'TESTSHIB_eppn': "teekkarit@first.invalid",
    'TESTSHIB_cn': "Temppu Ojanen Teettari", # used as fallback
    'TESTSHIB_displayName': "Teemudemus",
    'TESTSHIB_givenName': "Teemu",
    'TESTSHIB_sn': "Teekkari",
    'TESTSHIB_mail': "teemu.teekkari@first.invalid",
    'TESTSHIB_preferredLanguage': 'en',
    'TESTSHIB_schacHomeOrganization': 'first.invalid',
    'TESTSHIB_schacPersonalUniqueCode': shib_join(
        'urn:mace:example.invalid:schac:personalUniqueCode:int:libraryID:first.invalid:999999',
        'urn:mace:example.invalid:schac:personalUniqueCode:int:studentID:first.invalid:123453',
        'urn:mace:example.invalid:schac:personalUniqueCode:int:studentID:second.invalid:abcdef',
    ),
}

ENV_VARS = {
    'PREFIX': 'TESTSHIB_',
    'STUDENT_DOMAIN': 'first.invalid',
    'URL_DECODE': True,
}


@modify_settings(
    INSTALLED_APPS={'append': 'shibboleth_login'},
    AUTHENTICATION_BACKENDS={'append': 'shibboleth_login.auth_backend.ShibbolethAuthBackend'},
)
@override_settings(SHIBBOLETH_ENVIRONMENT_VARS=ENV_VARS)
class ShibbolethTest(TestCase):

    def setUp(self):
        self.user = User(
            username='meikalm8@first.invalid',
            email='matti@second.invalid',
            first_name='Matti',
            last_name='Sukunimi',
        )
        self.user.set_unusable_password()
        self.user.save()
        self.user.userprofile.student_id = '000'
        self.user.userprofile.organization = 'first.invalid'
        self.user.userprofile.save()

        self.login_url = reverse('shibboleth-login')

    def test_permission_is_denied_when_user_id_is_missing(self):
        meta = DEF_SHIBD_META.copy()
        del meta['TESTSHIB_eppn']
        response = self._get(meta)
        self.assertEqual(response.status_code, 403)
        self.assertEqual(User.objects.count(), 1)

    def test_permission_is_denied_when_user_id_does_not_contain_domain(self):
        meta = DEF_SHIBD_META.copy()
        meta['TESTSHIB_eppn'] = 'invalid-non-domain'
        response = self._get(meta)
        self.assertEqual(response.status_code, 403)
        self.assertEqual(User.objects.count(), 1)

    def test_permission_is_denied_when_user_id_is_way_too_long(self):
        meta = DEF_SHIBD_META.copy()
        meta['TESTSHIB_eppn'] = '-'.join(['invalid'] * 1000) + '@first.invalid'
        response = self._get(meta)
        self.assertEqual(response.status_code, 403)
        self.assertEqual(User.objects.count(), 1)

    def test_new_user_is_create_when_there_is_valid_data(self):
        meta = DEF_SHIBD_META.copy()
        response = self._get(meta)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(User.objects.count(), 2)
        user = User.objects.get(username='teekkarit@first.invalid')
        self.assertEqual(user.email, 'teemu.teekkari@first.invalid')
        self.assertEqual(user.first_name, 'Teemu')
        self.assertEqual(user.last_name, 'Teekkari')
        self.assertEqual(user.userprofile.student_id, '123453')

    def test_new_user_is_create_with_tuni_user_info(self):
        """
        Validate that shib login works with data obtained from Tampere universities
        """
        env_vars = ENV_VARS.copy()
        meta = DEF_SHIBD_META.copy()
        meta['TESTSHIB_schacPersonalUniqueCode'] = (
            'urn:schac:personalUniqueCode:int:studentID:uta.fi:A11111;'
            'urn:schac:personalUniqueCode:int:studentID:tamk.fi:222222;'
            'urn:schac:personalUniqueCode:int:studentID:tut.fi:333333;'
            'urn:schac:personalUniqueCode:int:studentID:uta.fi:44444'
        )
        tests = [
            ('uta.fi', 'A11111'), # first instance is selected
            ('tamk.fi', '222222'),
            ('tut.fi', '333333'),
        ]
        for domain, studentid in tests:
            with self.subTest(domain=domain, studentid=studentid):
                env_vars['STUDENT_DOMAIN'] = domain
                meta['TESTSHIB_schacHomeOrganization'] = domain
                with override_settings(SHIBBOLETH_ENVIRONMENT_VARS=env_vars):
                    response = self._get(meta)
                self.assertEqual(response.status_code, 302)
                self.assertEqual(User.objects.count(), 2)
                user = User.objects.get(username='teekkarit@first.invalid')
                self.assertEqual(user.userprofile.student_id, studentid)

    def test_new_user_is_create_even_with_lowercase_meta(self):
        meta = {k.lower(): v for k, v in DEF_SHIBD_META.items()}
        response = self._get(meta)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(User.objects.count(), 2)
        user = User.objects.get(username='teekkarit@first.invalid')
        self.assertEqual(user.email, 'teemu.teekkari@first.invalid')
        self.assertEqual(user.first_name, 'Teemu')
        self.assertEqual(user.last_name, 'Teekkari')
        self.assertEqual(user.userprofile.student_id, '123453')

    def test_email_is_create_when_when_email_is_missing(self):
        meta = DEF_SHIBD_META.copy()
        del meta['TESTSHIB_mail']
        response = self._get(meta)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(User.objects.count(), 2)
        user = User.objects.get(username='teekkarit@first.invalid')
        self.assertEqual(user.email, '{:d}@localhost'.format(user.id))
        self.assertEqual(user.first_name, 'Teemu')
        self.assertEqual(user.last_name, 'Teekkari')

    def test_cn_is_used_for_first_and_last_name_when_givename_and_sn_are_missing(self):
        meta = DEF_SHIBD_META.copy()
        del meta['TESTSHIB_givenName']
        del meta['TESTSHIB_sn']
        response = self._get(meta)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(User.objects.count(), 2)
        user = User.objects.get(username='teekkarit@first.invalid')
        self.assertEqual(user.first_name, 'Temppu')
        self.assertEqual(user.last_name, 'Ojanen Teettari')

    def test_cn_is_used_for_first_name_when_givename_is_missing(self):
        meta = DEF_SHIBD_META.copy()
        del meta['TESTSHIB_givenName']
        response = self._get(meta)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(User.objects.count(), 2)
        user = User.objects.get(username='teekkarit@first.invalid')
        self.assertEqual(user.first_name, 'Temppu')
        self.assertEqual(user.last_name, 'Teekkari')

    def test_displayname_is_used_for_first_name_when_givename_and_cn_are_missing(self):
        meta = DEF_SHIBD_META.copy()
        del meta['TESTSHIB_givenName']
        del meta['TESTSHIB_cn']
        response = self._get(meta)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(User.objects.count(), 2)
        user = User.objects.get(username='teekkarit@first.invalid')
        self.assertEqual(user.first_name, 'Teemudemus')
        self.assertEqual(user.last_name, 'Teekkari')

    def test_no_student_id_is_set_when_it_is_missing_from_shib(self):
        meta = DEF_SHIBD_META.copy()
        del meta['TESTSHIB_schacPersonalUniqueCode']
        response = self._get(meta)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(User.objects.count(), 2)
        user = User.objects.get(username='teekkarit@first.invalid')
        self.assertEqual(user.email, 'teemu.teekkari@first.invalid')
        self.assertEqual(user.first_name, 'Teemu')
        self.assertEqual(user.last_name, 'Teekkari')
        self.assertEqual(user.userprofile.student_id, None)

    def test_second_domain_student_id_is_used_when_setting_is_changed(self):
        meta = DEF_SHIBD_META.copy()
        meta['TESTSHIB_eppn'] = self.user.username
        env_vars = ENV_VARS.copy()
        env_vars['STUDENT_DOMAIN'] = 'second.invalid'
        meta['TESTSHIB_schacHomeOrganization'] = 'second.invalid'
        with override_settings(SHIBBOLETH_ENVIRONMENT_VARS=env_vars):

            response = self._get(meta)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(User.objects.count(), 1)
        user = User.objects.first()
        self.assertEqual(user.userprofile.student_id, 'abcdef')

    def test_last_name_is_not_updated_when_sn_is_missing(self):
        meta = DEF_SHIBD_META.copy()
        meta['TESTSHIB_eppn'] = self.user.username
        del meta['TESTSHIB_sn']
        response = self._get(meta)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(User.objects.count(), 1)
        user = User.objects.first()
        self.assertEqual(user.email, 'teemu.teekkari@first.invalid')
        self.assertEqual(user.first_name, 'Teemu')
        self.assertEqual(user.last_name, 'Sukunimi')
        self.assertEqual(user.userprofile.student_id, '123453')

    def test_values_are_not_updated_when_they_are_missing(self):
        meta = DEF_SHIBD_META.copy()
        meta['TESTSHIB_eppn'] = self.user.username
        del meta['TESTSHIB_givenName']
        del meta['TESTSHIB_sn']
        del meta['TESTSHIB_schacPersonalUniqueCode']
        response = self._get(meta)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(User.objects.count(), 1)
        user = User.objects.first()
        self.assertEqual(user.email, 'teemu.teekkari@first.invalid')
        self.assertEqual(user.first_name, 'Matti')
        self.assertEqual(user.last_name, 'Sukunimi')
        self.assertEqual(user.userprofile.student_id, '000')

    def test_unicode_values_are_supported_for_names(self):
        meta = DEF_SHIBD_META.copy()
        meta['TESTSHIB_eppn'] = self.user.username
        meta['TESTSHIB_givenName'] = 'Mänty'
        meta['TESTSHIB_sn'] = 'Hölmöläinen'
        response = self._get(meta)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(User.objects.count(), 1)
        user = User.objects.first()
        self.assertEqual(user.email, 'teemu.teekkari@first.invalid')
        self.assertEqual(user.first_name, 'Mänty')
        self.assertEqual(user.last_name, 'Hölmöläinen')

    @override_settings(SHIBBOLETH_LOGIN={'ALLOW_SEARCH_WITH_EMAIL': True})
    def test_old_user_found_using_email(self):
        meta = DEF_SHIBD_META.copy()
        email = self.user.email
        meta['TESTSHIB_mail'] = email
        response = self._get(meta)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(User.objects.count(), 1)
        user = User.objects.first()
        self.assertEqual(user.email, email)
        self.assertEqual(user.first_name, 'Teemu')
        self.assertEqual(user.last_name, 'Teekkari')
        self.assertEqual(user.userprofile.student_id, '123453')

    def test_permission_is_denied_when_user_is_inactive(self):
        self.user.is_active = False
        self.user.save()
        meta = DEF_SHIBD_META.copy()
        meta['TESTSHIB_eppn'] = self.user.username
        response = self._get(meta)
        self.assertEqual(response.status_code, 403)
        self.assertEqual(User.objects.count(), 1)

    def _get(self, meta):
        meta = {key: quote(value) for key, value in meta.items()}
        return self.client.generic('GET', self.login_url, **meta)



@modify_settings(
    INSTALLED_APPS={'append': 'shibboleth_login'},
    AUTHENTICATION_BACKENDS={'append': 'shibboleth_login.auth_backend.ShibbolethAuthBackend'},
)
class ShibbolethSettingsTest(TestCase):

    def test_SHIBBOLETH_VARIABLES_URL_ENCODED_is_migrated(self):
        settings = dict(
            SHIBBOLETH_VARIABLES_URL_ENCODED = 'test-value',
            SHIBBOLETH_ENVIRONMENT_VARS = {
                'STUDENT_DOMAIN': ENV_VARS['STUDENT_DOMAIN'],
                'PREFIX': ENV_VARS['PREFIX'],
            },
        )
        with override_settings(**settings):
            from shibboleth_login.apps import env_settings # pylint: disable=import-outside-toplevel
            self.assertEqual(env_settings.URL_DECODE, 'test-value')

    def test_old_settings_are_parsed_correctly(self):
        settings = dict(
            SHIB_USER_ID_KEY = 'RANDOM_EPPN',
            SHIB_FIRST_NAME_KEY = 'RANDOM_GIVENNAME',
            SHIB_LAST_NAME_KEY = 'RANDOM_SN',
            SHIB_MAIL_KEY = 'RANDOM_MAIL',
            SHIB_STUDENT_ID_KEY = 'RANDOM_SCHACPERSONALUNIQUECODE',
            SHIBBOLETH_ENVIRONMENT_VARS = {'STUDENT_DOMAIN': ENV_VARS['STUDENT_DOMAIN']},
        )
        with override_settings(**settings):
            from shibboleth_login.apps import env_settings # pylint: disable=import-outside-toplevel
            self.assertEqual(env_settings.PREFIX, 'RANDOM_')
            self.assertEqual(env_settings.USER_ID, 'EPPN')
            self.assertEqual(env_settings.FIRST_NAME, 'GIVENNAME')
            self.assertEqual(env_settings.LAST_NAME, 'SN')
            self.assertEqual(env_settings.EMAIL, 'MAIL')
            self.assertEqual(env_settings.STUDENT_IDS, 'SCHACPERSONALUNIQUECODE')

    def test_old_settings_with_http_prefix_are_parsed_correctly(self):
        settings = dict(
            SHIB_USER_ID_KEY = 'HTTP_SHIB_EPPN',
            SHIB_FIRST_NAME_KEY = 'HTTP_SHIB_GIVENNAME',
            SHIB_LAST_NAME_KEY = 'HTTP_SHIB_SN',
            SHIB_MAIL_KEY = 'HTTP_SHIB_MAIL',
            SHIB_STUDENT_ID_KEY = 'HTTP_SHIB_SCHACPERSONALUNIQUECODE',
            SHIBBOLETH_ENVIRONMENT_VARS = {'STUDENT_DOMAIN': ENV_VARS['STUDENT_DOMAIN']},
        )
        with override_settings(**settings):
            from shibboleth_login.apps import env_settings # pylint: disable=import-outside-toplevel
            self.assertEqual(env_settings.PREFIX, 'HTTP_SHIB_')
            self.assertEqual(env_settings.USER_ID, 'EPPN')
            self.assertEqual(env_settings.FIRST_NAME, 'GIVENNAME')
            self.assertEqual(env_settings.LAST_NAME, 'SN')
            self.assertEqual(env_settings.EMAIL, 'MAIL')
            self.assertEqual(env_settings.STUDENT_IDS, 'SCHACPERSONALUNIQUECODE')
