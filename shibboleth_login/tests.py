import urllib.parse

from django.conf import settings
from django.contrib.auth.models import User
from django.core.urlresolvers import reverse
from django.test import TestCase, modify_settings
from django.utils import timezone


DEF_SHIBD_META = {
    'SHIB_cn': 'Teemu Teekkari',
    'SHIB_mail': 'teemu.teekkari@aalto.fi',
    'Shib-Authentication-Method': 'urn:oasis:names:tc:SAML:2.0:ac:classes:PasswordProtectedTransport',
    'Shib-Identity-Provider': 'https://locahost/idp/shibboleth',
    'SHIB_displayName': 'Teemudemus',
    'Shib-AuthnContext-Class': 'urn:oasis:names:tc:SAML:2.0:ac:classes:PasswordProtectedTransport',
    'SHIB_schacPersonalUniqueCode': 'urn:mace:terena.org:schac:personalUniqueCode:int:studentID:aalto.fi:123453',
    'Shib-Session-Index': '_941d95bafed0b1787c81541e627a8c8b',
    'SHIB_sn': 'Teekkari',
    'SHIB_givenName': 'Teemu',
    'Shib-Application-ID': 'default',
    'Shib-Authentication-Instant': str(timezone.now()),
    'Shib-Session-ID': '_92d7c6a832b5c7dafea59ea12ca1289e',
    'SHIB_preferredLanguage': 'fi',
    'SHIB_logouturl': 'https://localhost/idp/aalto_logout.jsp',
    'SHIB_eppn': 'teekkarit@aalto.fi',
}

@modify_settings(
    INSTALLED_APPS={'append': 'shibboleth_login'},
    AUTHENTICATION_BACKENDS={'append': 'shibboleth_login.auth_backend.ShibbolethAuthBackend'},
)
class ShibbolethTest(TestCase):

    def setUp(self):
        self.user = User(
            username='meikalm8@aalto.fi',
            email='',
            first_name='Matti',
            last_name='Sukunimi',
        )
        self.user.set_unusable_password()
        self.user.save()
        self.user.userprofile.student_id = '000'
        self.user.userprofile.save()

        self.login_url = reverse('shibboleth-login')

    def test_invalid(self):
        meta = DEF_SHIBD_META.copy()
        del meta['SHIB_eppn']
        response = self._get(meta)
        self.assertEqual(response.status_code, 403)
        self.assertEqual(User.objects.count(), 1)

    def test_valid_new(self):
        meta = DEF_SHIBD_META.copy()
        response = self._get(meta)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(User.objects.count(), 2)
        user = User.objects.get(username='teekkarit@aalto.fi')
        self.assertEqual(user.email, 'teemu.teekkari@aalto.fi')
        self.assertEqual(user.first_name, 'Teemu')
        self.assertEqual(user.last_name, 'Teekkari')
        self.assertEqual(user.userprofile.student_id, '123453')

    def test_without_email(self):
        meta = DEF_SHIBD_META.copy()
        del meta['SHIB_mail']
        del meta['SHIB_givenName']
        response = self._get(meta)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(User.objects.count(), 2)
        user = User.objects.get(username='teekkarit@aalto.fi')
        self.assertEqual(user.email, '{:d}@localhost'.format(user.id))
        self.assertEqual(user.first_name, '')
        self.assertEqual(user.last_name, 'Teekkari')
        self.assertEqual(user.userprofile.student_id, '123453')

    def test_without_student_id(self):
        meta = DEF_SHIBD_META.copy()
        del meta['SHIB_schacPersonalUniqueCode']
        response = self._get(meta)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(User.objects.count(), 2)
        user = User.objects.get(username='teekkarit@aalto.fi')
        self.assertEqual(user.email, 'teemu.teekkari@aalto.fi')
        self.assertEqual(user.first_name, 'Teemu')
        self.assertEqual(user.last_name, 'Teekkari')
        self.assertEqual(user.userprofile.student_id, None)

    def test_valid_old(self):
        meta = DEF_SHIBD_META.copy()
        meta['SHIB_eppn'] = self.user.username
        del meta['SHIB_sn']
        response = self._get(meta)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(User.objects.count(), 1)
        user = User.objects.first()
        self.assertEqual(user.email, 'teemu.teekkari@aalto.fi')
        self.assertEqual(user.first_name, 'Teemu')
        self.assertEqual(user.last_name, 'Sukunimi')
        self.assertEqual(user.userprofile.student_id, '123453')

    def test_nonascii(self):
        meta = DEF_SHIBD_META.copy()
        meta['SHIB_eppn'] = self.user.username.encode('utf-8')
        del meta['SHIB_givenName']
        meta['SHIB_sn'] = 'Meikäläinen'
        del meta['SHIB_schacPersonalUniqueCode']
        response = self._get(meta)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(User.objects.count(), 1)
        user = User.objects.first()
        self.assertEqual(user.email, 'teemu.teekkari@aalto.fi')
        self.assertEqual(user.first_name, 'Matti')
        self.assertEqual(user.last_name, 'Meikäläinen')
        self.assertEqual(user.userprofile.student_id, '000')

    def test_inactive(self):
        self.user.is_active = False
        self.user.save()
        meta = DEF_SHIBD_META.copy()
        meta['SHIB_eppn'] = self.user.username.encode('utf-8')
        response = self._get(meta)
        self.assertEqual(response.status_code, 403)
        self.assertEqual(User.objects.count(), 1)

    def _get(self, meta):
        if settings.SHIBBOLETH_VARIABLES_URL_ENCODED:
            for key in meta.keys():
                meta[key] = urllib.parse.quote(meta[key])
        return self.client.generic('GET', self.login_url, **meta)
