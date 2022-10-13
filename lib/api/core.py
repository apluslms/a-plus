from distutils.version import LooseVersion as _version

from rest_framework import exceptions
from rest_framework.renderers import JSONRenderer
from rest_framework.versioning import AcceptHeaderVersioning, URLPathVersioning
from rest_framework.negotiation import DefaultContentNegotiation
from rest_framework.compat import unicode_http_header
from rest_framework.utils import mediatypes


# define this here as it's project dependent and not installation
# there is no point to redefine it ever
APLUS_JSON_TYPE = 'application/vnd.aplus+json'


class _MediaType(mediatypes._MediaType):
    """
    Slightly modified private _MediaType class from Django REST framework.
    This version has full_type property for convenience.
    """

    @property
    def full_type(self):
        return "%s/%s" % (self.main_type, self.sub_type)

    @full_type.setter
    def full_type(self, value):
        self.main_type, _sep, self.sub_type = value.partition('/')

    @full_type.deleter
    def full_type(self):
        self.main_type = '*'
        self.sub_type = '*'


class APlusJSONRenderer(JSONRenderer):
    """
    Just mark that our own responses are aplus json and not normal one
    """
    media_type = APLUS_JSON_TYPE


class APlusVersioning(URLPathVersioning):
    """
    Our versioning class takes major version from URL real api version is
    then read from settings based on major version.

    If client provides version in accept header (only with correct media type)
    it will be tested that it is less or equal to what we support.

    If version in URL or in Accept header is not supported, corect html error
    is returned. (URL case should not be possible if urls.py is correct).

    Task of telling the client our api version in content type is also done here.
    This is due to design of django rest framework.
    """
    invalid_accept_version_message = AcceptHeaderVersioning.invalid_version_message

    def determine_version(self, request, *args, **kwargs):
        major_version = super().determine_version(request, *args, **kwargs)
        api_version = self.allowed_versions[major_version]

        ## get and update version in request media type
        # this is only location where need to check the requested version and we
        # update the version so the respond content type has the correct version
        media_type = _MediaType(request.accepted_media_type)
        accept_version = unicode_http_header(media_type.params.get(self.version_param, ''))
        media_type.params[self.version_param] = api_version.encode('ascii')
        # dict values in _MediaType.params must be of type bytes.
        # DRF calls val.decode('ascii') on them in _MediaType.__str__
        request.accepted_media_type = str(media_type)

        if accept_version:
            accept_major_version = accept_version.split('.', 1)[0]
            if accept_major_version != major_version or _version(api_version) < _version(accept_version):
                raise exceptions.NotAcceptable(self.invalid_accept_version_message)

        return major_version


class APlusContentNegotiation(DefaultContentNegotiation):
    """
    We add to default content negotiation feature will update all application/json
    with our own type. This is not the optimal way to handle the problem.
    Real solution would do it in media_type_matches function in django rest framework
    """
    def get_accept_list(self, request):
        accept_list = super().get_accept_list(request)
        accepts = []
        for accept in accept_list:
            if accept.startswith('application/json'):
                # convert generic json to aplus json type
                mt = _MediaType(accept)
                mt.full_type = APLUS_JSON_TYPE
                mt.params.pop('version', None) # ignore version for generic json types
                accept = str(mt)
            accepts.append(accept)
        return accepts
