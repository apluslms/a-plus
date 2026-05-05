DEBUG = True
#SECRET_KEY = 'not a very secret key'
ADMINS = (
)
#ALLOWED_HOSTS = ["*"]

BASE_URL = 'http://localhost:8000'
SERVICE_BASE_URL = 'http://plus:8000'

from os import environ
if environ.get('USE_GITMANAGER') == 'true':
    GITMANAGER_URL = 'http://gitmanager:8070'
else:
    GITMANAGER_URL = None

# Authentication and authentication library settings.
APLUS_AUTH_LOCAL = {
    "UID": "aplus",
    "PRIVATE_KEY": """-----BEGIN RSA PRIVATE KEY-----
MIIEowIBAAKCAQEAnME9k+VaxbUD2fGDgpKHRi6cE4T6HZzqWDpvtOShhoHSYQ6V
lX0YnDQYwdDoTTK+XIBG2uS8W+3CsvpxjpHF8Ny5xzxNGZTeqSn8A08BvoQ5cX7b
nXOYUb4x2Pp/00WwaQseumUNP+ep/jCV+aqviWzOmX9p8zZGdFghvplbt9A173df
4t6kICK11hUm14mpUtL/bCQ2xsUEmPGX+zw8V1kynwJp2AaBuFVpkKDjHyHQJ+yo
tou01Vksp1kYoX21odjoZCivArEjuwzDEoHt6WHPLnwvkBYouNA9jgR63mS1rW1P
iloDlNNMFW1nR+AHjTfVSKKatnswO3JVLxYeqwIDAQABAoIBAGAAdT8Do2EcKFys
7hbkuJZB63KE6U2DkX4xY8KMl2QyU+7/KJth/tWDjnn9AJhu8GjkYwCiP72pUqmc
ejmPi4OlGt4rTyjQpMFDpkU8eNv+TNP2lnfKmMnPSuYRHIH+1ziuB8auJrwxnEnB
5cf/QfxPOASIJRI/9kxAwYHimGps02tzSpIKyJapGXUhYpuh8CPglb/YELoIipAF
ds66WXIgw/KGDm/VG3iF/wmRpIFQ2vFsZU11UpPwgk7dQMAvnNJL+jqn+o5n54DN
XATYgV0ooNwxJS6J14bLomutMScwOcI+E0aWpYTa1Cdndz5QAfWH/1xgQn4/VxC6
9s2JiSECgYEAzuRM3oCUBPCW0X7xwPT2ZHOGmwEINxptqzaJYuzTEfN8J2NtwqXm
0gR/q8p8iX4OY1QJuJKY2i2lXSOQmR7y6/r8c4U4SQCIpDfGfrs71FCddjwfIZG/
+AM8M4WNS/UP0bU2daEVcz8xK0PgDAo5uo8onpLKLtTdIY3rhQVrCzsCgYEAwfZj
Sjx+BpXmEMgqo4yHzXSK6Czy9UHOIDAaNbssxQ0JSeVxlHN7z3sV46MyuDlQUnPF
m042cxdgf2CUHeO0Ys+ebPU5FsUpNOcrhkVFdflEvVVqjGd3uEXdJo3fnsgoCicR
uh/nUiTwtP6PEWihYad568Ic7hTsoltwh+Ujo1ECgYEApAi8rZkyQqxiV52Xnc5a
4I/8BD+QPOg2VY465XUxcEUlhbE+oBqbZJ5uf01e6kBIthY2UuHgUPPp7Wu6RL0W
C2WG7SyN0Mucit8yAN8Ac7iq78iBQkNl+gTOoWbc/YFCVpmfoSnjcOmEWXJKXCFr
XfANW5S0uubIoMb+GgyOr2sCgYBTM+85vCNPjePIFSV9TN5AexrPJ+D85kKWuiu0
GtvEl6gBZARJ6xQUV7d3E93A+w0CoZkF2xIuYrvJSFOhUrlhnbBXCwZ3RxI7GGMq
UPLP/aLIGSkAm63WhVmtnTRs9219lW7cSa1AJop/Caezjw+TRXVedcFVO/KaXuEx
2lBkUQKBgCCUApTShkBTEbIAht2XBXe1e667Z0FHLUWBqSE2Q3pkWtHe1Rg85386
92/P1ku3ijVBbw5ybYwFymhdqxRWuYIHAPy1tGiz4UKw8EE8BXl1Dzm7jL3BA4fZ
qGdEWd23bWuW5J+wbVaOSg2R5Z1UTYr7dcXKwF0x8M7hstyRJbb7
-----END RSA PRIVATE KEY-----""",
    "PUBLIC_KEY": """-----BEGIN PUBLIC KEY-----
MIIBIjANBgkqhkiG9w0BAQEFAAOCAQ8AMIIBCgKCAQEAnME9k+VaxbUD2fGDgpKH
Ri6cE4T6HZzqWDpvtOShhoHSYQ6VlX0YnDQYwdDoTTK+XIBG2uS8W+3CsvpxjpHF
8Ny5xzxNGZTeqSn8A08BvoQ5cX7bnXOYUb4x2Pp/00WwaQseumUNP+ep/jCV+aqv
iWzOmX9p8zZGdFghvplbt9A173df4t6kICK11hUm14mpUtL/bCQ2xsUEmPGX+zw8
V1kynwJp2AaBuFVpkKDjHyHQJ+yotou01Vksp1kYoX21odjoZCivArEjuwzDEoHt
6WHPLnwvkBYouNA9jgR63mS1rW1PiloDlNNMFW1nR+AHjTfVSKKatnswO3JVLxYe
qwIDAQAB
-----END PUBLIC KEY-----""",
    "DISABLE_LOGIN_CHECKS": False,
    "DISABLE_JWT_SIGNING": False,
    # List all trusted public keys with an UID.
    "UID_TO_KEY": {
        "grader": """-----BEGIN PUBLIC KEY-----
MIIBIjANBgkqhkiG9w0BAQEFAAOCAQ8AMIIBCgKCAQEAweaxw/6dSfIWegPg6y9w
rsjSNDZaShQzH9/HsOjcPeIrO8ZuxT5iZfaPji7y5m+VYaG+76q0harls9uvYdcp
dRD8inrUutd6LvMUInyD6h/OVhlOxvwMzh+UVpE9OnzignGCVpWVqsepJ5/IMf+H
4OhOg+O7b28eGIYcyfkkrLviNAoT8Ml7itQnOzePn+3IvuoEX+3CGXNTt6S7Mm/j
2W6vZ8/ZtQuoQhbe3wkDCk2PAQaPuXlLvbQnQyYkRiIntUQexaokfOwXjSoBzOaS
cGBcQ7A3ua3NPAiQl5mI+tj2yOg+qljUIAEmUXbrrEGqGvYDX0VXlP9TtCU8EP/F
6wIDAQAB
-----END PUBLIC KEY-----""",
        "gitmanager": """-----BEGIN PUBLIC KEY-----
MIIBIjANBgkqhkiG9w0BAQEFAAOCAQ8AMIIBCgKCAQEAsaVdUeIDB1TluqYgkxRa
0JMxIoa1f6V0UpfR6eoa/RKyZS3A2mp9Mjt9OXRB4sG9L+OQRm4kx03M2QyFPEsz
mcehmZ1kWXyXJHyhqnaUACm2bUKSjexsfoHjZV4/KaFe7vdyPwXhpVQ876/DKApk
OF6ugfeETx5tSfgWMerOjV6lqrgGEi9OvuymvJlY+Jgxi6uhZTbZntcQ0Dbpp7j5
XHAshtEP2NOpefG/5v03zSILs9oUaoAOSb2VMke9+/pg20vYYzYEcNbqUVMal88L
kb3lV9aulPi7rH+FGRZuI0/wFzWcuLSupF1+YcwGprsm3seead90dRh6gYHXk8v1
2wIDAQAB
-----END PUBLIC KEY-----""",
    },
    # A mapping of URLs to UIDs.
    "TRUSTING_REMOTES": {
        "http://grader:8080": "grader",
        "http://gitmanager:8070": "gitmanager",
    },
}

STATIC_ROOT = '/local/aplus/static/'
MEDIA_ROOT = '/local/aplus/media/'

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': 'aplus',
    },
}

CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.filebased.FileBasedCache',
        'LOCATION': '/run/aplus/django-cache',
    },
}

REMOTE_PAGE_HOSTS_MAP = {
    "grader:8080": "localhost:8080",
    "gitmanager:8070": "localhost:8070",
}

#CELERY_BROKER_URL = "amqp://"

LOGGING['loggers'].update({
    '': {
        'level': 'INFO',
        'handlers': ['debug_console'],
        'propagate': True,
    },
    #'django.db.backends': {
    #    'level': 'DEBUG',
    #},
})

# kate: space-indent on; indent-width 4;
# vim: set expandtab ts=4 sw=4:
