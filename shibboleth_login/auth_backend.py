import logging

from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.auth.backends import ModelBackend


logger = logging.getLogger('aplus.shibboleth')

USER_ID_KEY = 'SHIB_USER_ID_KEY'
FIRST_NAME_KEY = 'SHIB_FIRST_NAME_KEY'
LAST_NAME_KEY = 'SHIB_LAST_NAME_KEY'
MAIL_KEY = 'SHIB_MAIL_KEY'
STUDENT_ID_KEY = 'SHIB_STUDENT_ID_KEY'

# These keys may be overridden in Django settings.
DEFAULT_KEYS = {
    USER_ID_KEY: 'SHIB_eppn',
    MAIL_KEY: 'SHIB_mail',
    FIRST_NAME_KEY: 'SHIB_displayName',
    LAST_NAME_KEY: 'SHIB_sn',
    STUDENT_ID_KEY: 'SHIB_schacPersonalUniqueCode', 
}


class ShibbolethAuthBackend(ModelBackend):
    """
    Authenticates the trusted user from the Shibboleth middleware headers.
    Creates a new user or updates changed fields on an existing user.
    
    """
    def authenticate(self, shibd_meta=None):
        if not shibd_meta:
            return None
        user_save_flag = False
        
        username = self._parse(shibd_meta, USER_ID_KEY)
        if not username:
            logger.warning('Shibboleth login attempt without a user id.')
            return None
        
        UserModel = get_user_model()
        user = UserModel._default_manager.filter(username=username).first()
        if not user:
            logger.info('Creating a new Shibboleth authenticated user: %s', username)
            user = UserModel._default_manager.create_user(username, '')
            
            missing_email_replacement = '{:d}@localhost'.format(user.id)
            user.email = self._parse(shibd_meta, MAIL_KEY, missing_email_replacement)
            user.set_unusable_password()
            user_save_flag = True
        else:
            email = self._parse(shibd_meta, MAIL_KEY)
            if email and email != user.email:
                user.email = email
                user_save_flag = True

        first_name = self._parse(shibd_meta, FIRST_NAME_KEY)
        if first_name and first_name != user.first_name:
            user.first_name = first_name
            user_save_flag = True

        last_name = self._parse(shibd_meta, LAST_NAME_KEY)
        if last_name and last_name != user.last_name:
            user.last_name = last_name
            user_save_flag = True
        
        if user_save_flag:
            user.save()
        
        profile = user.userprofile
        student_id = self._parse(shibd_meta, STUDENT_ID_KEY, '').split(':')[-1]
        if student_id and student_id != profile.student_id:
            profile.student_id = student_id
            profile.save()
        
        return user

    def _parse(self, shibd_meta, key_name, default_value=None):
        key = self._key(key_name)
        if key in shibd_meta:
            return shibd_meta[key]
        return default_value

    def _key(self, name):
        try:
            return getattr(settings, name)
        except AttributeError:
            return DEFAULT_KEYS[name]
