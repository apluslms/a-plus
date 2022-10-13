import logging

from django.contrib.auth import get_user_model
from django.contrib.auth.backends import ModelBackend

from .apps import app_settings, env_settings
from .parser import Parser


logger = logging.getLogger('aplus.shibboleth')


class ShibbolethAuthBackend(ModelBackend):
    """
    Authenticates the trusted user from the Shibboleth middleware headers.
    Creates a new user or updates changed fields on an existing user.

    """
    def authenticate(self, request, shibd_meta=None): # noqa: MC0001
        if not shibd_meta:
            return None
        user_save_flag = False

        UserModel = get_user_model()
        username_field = getattr(UserModel, 'USERNAME_FIELD', 'username')
        email_field = getattr(UserModel, 'EMAIL_FIELD', 'email')
        username_len = UserModel._meta.get_field(username_field).max_length
        email_len = UserModel._meta.get_field(email_field).max_length
        first_name_len = UserModel._meta.get_field('first_name').max_length
        last_name_len = UserModel._meta.get_field('last_name').max_length

        parser = Parser(env=shibd_meta,
                        urldecode=env_settings.URL_DECODE)

        # resolve username
        username = self._get_scoped_limited(parser, env_settings.USER_ID, username_len)
        if not username:
            return None
        username = username.lower()

        # resolve email
        email = self._get_scoped_limited(parser, env_settings.EMAIL, email_len)
        if email:
            email = UserModel.objects.normalize_email(email)

        # find user
        try:
            user = UserModel.objects.filter(**{username_field: username}).get()
        except UserModel.DoesNotExist:
            user = None

        # fallback, find user with email
        if not user and app_settings.ALLOW_SEARCH_WITH_EMAIL:
            qs = UserModel.objects.filter(**{email_field: email})
            if qs.count() == 1:
                user = qs.first()

        # create missing users
        if not user and app_settings.ALLOW_CREATE_NEW_USERS:
            logger.info('Creating a new Shibboleth authenticated user: %s <%s>',
                username, email)
            user = UserModel(**{
                username_field: username,
                email_field: email or '',
            })
            if not email:
                user.save()
                # TODO: use real domain with support for this and pseudonymized users
                user.email = '{:d}@localhost'.format(user.id)
            user.set_unusable_password()
            user_save_flag = True

        if not user:
            return None

        # update email
        if email and email != user.email:
            user.email = email
            user_save_flag = True

        # update first_name
        first_name = ' '.join(parser.get_values(env_settings.FIRST_NAME, ''))[:first_name_len]
        if first_name and first_name != user.first_name:
            user.first_name = first_name
            user_save_flag = True

        # update last_name
        last_name = ' '.join(parser.get_values(env_settings.LAST_NAME, ''))[:last_name_len]
        if last_name and last_name != user.last_name:
            user.last_name = last_name
            user_save_flag = True

        # if not first_name or last_name, fallback to cn and displayName
        if not user.first_name or not user.last_name:
            # best effort to find best possible name..
            full_name = max((
                ' '.join(parser.get_values(env_settings.FULL_NAME, '')),
                ' '.join(parser.get_values(env_settings.COMMON_NAME, '')),
            ), key=len)
            first_, __, last_ = full_name.partition(' ')
            if not user.first_name:
                user.first_name = first_[:first_name_len]
            if not user.last_name:
                user.last_name = last_[:last_name_len]
            user_save_flag = True

        if user_save_flag:
            # TODO: write better error reporting, when there is a validator to raise something
            user.full_clean()
            user.save()

        homeorg = parser.get_single_value(env_settings.HOME_ORGANIZATION, '')
        profile = user.userprofile
        sid_filters = env_settings.STUDENT_FILTERS.copy()
        # verifies that domain in personal code URN matches home organization
        # (also, for minimal change to existing student filters code)
        sid_filters[1] = homeorg
        try:
            student_ids = parser.get_urn_values(
                env_settings.STUDENT_URN,
                env_settings.STUDENT_IDS,
                filters=sid_filters)
        except KeyError as error:
            logger.warning("Did not find a student id for user '%s', missing field '%s'",
                username, error)
            student_ids = ()
        except ValueError as error:
            logger.warning("Did not find a student id for user '%s', invalid data: %s",
                username, error)
            student_ids = ()
        # example: ('123456', 'aalto.fi', 'studentID', 'int', 'mace:terena.org')
        # -> (value (student number), the domain, id type, int|local, schema namespace)
        student_id = next(iter(student_ids), (None,))[0]
        user_save_flag = False
        if student_id and student_id != profile.student_id:
            profile.student_id = student_id
            user_save_flag = True

        if homeorg != profile.organization:
            profile.organization = homeorg
            user_save_flag = True

        if user_save_flag:
            profile.save()

        return user


    def _get_scoped_limited(self, parser, name, max_len):
        try:
            value = parser.get_single_value(name)
        except KeyError:
            logger.warning("Shibboleth login attempt without %s%s.",
                env_settings.PREFIX, name)
            return None
        except ValueError as error:
            logger.warning("Shibboleth login attempt with multiple values for %s%s: %s",
                env_settings.PREFIX, name, str(error)[:512])
            return None
        if not value:
            logger.warning("Shibboleth login attempt with empty %s%s.",
                env_settings.PREFIX, name)
            return None
        if len(value) > max_len:
            logger.warning("Shibboleth login attempt with too long %s%s (%d > %d).",
                env_settings.PREFIX, name, len(value), max_len)
            return None
        if '@' not in value:
            logger.warning("Shibboleth login attempt without domain in %s%s (%s).",
                env_settings.PREFIX, name, value)
            return None
        return value
