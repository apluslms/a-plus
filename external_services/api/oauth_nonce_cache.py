from django.core.cache import cache

class OAuthNonceCache:
    '''Cache for OAuth nonce values so that a received nonce may be checked
    against previously seen nonces.
    In OAuth1, the nonce value MUST be unique across all requests with the
    same timestamp, client credentials, and token combinations.
    Since LTI 1.1 does not use OAuth tokens, tokens are ignored here.
    Uses the default cache configured in Django.'''

    CACHE_TIMEOUT_SECONDS = 60 * 10 # 10 minutes

    def __init__(self, nonce, timestamp, client_secret):
        self.nonce = nonce
        self.timestamp = timestamp
        self.client_secret = client_secret

    def _get_key(self):
        return 'lti-nonce_{nonce}:{timestamp}:{client_secret}'.format(
            nonce=self.nonce,
            timestamp=self.timestamp,
            client_secret=self.client_secret,
        )

    def nonce_used(self):
        '''Return True if the nonce has already been used.
        Return False if it has not been used, in which case it is also added to the cache.'''
        return not cache.add(self._get_key(), True, self.CACHE_TIMEOUT_SECONDS)
