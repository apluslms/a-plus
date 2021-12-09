import logging
from typing import Any, Optional
from urllib.parse import urlparse

from aplus_auth import settings as auth_settings
from aplus_auth.payload import Payload
from aplus_auth.requests import jwt_sign, Session as SessionBase, with_session
from django.conf import settings


logger = logging.getLogger("aplus.aplus_auth")


def _get_key(url: str) -> Optional[str]:
    alias = settings.URL_TO_ALIAS.get(url, url)
    return settings.ALIAS_TO_PUBLIC_KEY.get(alias)


def url_to_audience(url: str) -> str:
    """
    Turns an URL to the RSA key used as an audience in JWT tokens.
    """
    parsed_url = urlparse(url)
    key = _get_key(f"{parsed_url.netloc}{parsed_url.path}")
    if key is None:
        key = _get_key(parsed_url.netloc)
    if key is None and parsed_url.hostname is not None:
        key = _get_key(parsed_url.hostname)
    if key is None:
        raise KeyError(f"Could not find public key for {url}")
    return key


def audience_to_alias(audience: str) -> str:
    """
    Turns an RSA key used as an audience in JWT tokens to a alias defined in
    django settings.
    """
    try:
        return next((k for k,v in settings.ALIAS_TO_PUBLIC_KEY.items() if v == audience))
    except StopIteration:
        return audience


class Session(SessionBase):
    @classmethod
    def get_token(cls, url: str, payload: Payload) -> str:
        if payload.sub is None:
            payload.sub = auth_settings().PUBLIC_KEY

        try:
            payload.aud = url_to_audience(url)
        except KeyError as e:
            logger.warning(e)

        return jwt_sign(payload)


request = with_session(Session, Session.request)
get = with_session(Session, Session.get)
post = with_session(Session, Session.post)
put = with_session(Session, Session.put)
options = with_session(Session, Session.options)
delete = with_session(Session, Session.delete)
head = with_session(Session, Session.head)
patch = with_session(Session, Session.patch)
