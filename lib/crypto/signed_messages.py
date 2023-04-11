import hashlib
import hmac
import random
import time
from base64 import urlsafe_b64encode, urlsafe_b64decode
from django.conf import settings


__all__ = [
    'get_signed_message',
    'get_valid_message',
]


### HMAC signed messages
# Messages are signed using installation secret.
#
# Signature is calculated from current time, nonce and payload message
#
# Format of trasport structure:
#   4 bytes: time
#   1 byte : nonce len
#   N bytes: nonce (where N is 4 or more)
#   N bytes: sign  (where N is HASH_SIZE)
#   N bytes: message encoded utf8
# This byte array is base64 encoded (urlsafe_b64encode)
#
# We use 1 byte for nonce so we can change it's szze without
# breaking messages still enroute.

NONCE_BYTES = 4
HASH_METHOD = hashlib.sha256
HASH_SIZE = HASH_METHOD().digest_size

def _signature(stamp, nonce, payload):
    return hmac.new(
        settings.SECRET_KEY.encode('utf-8'),
        msg=stamp + nonce + payload,
        digestmod=HASH_METHOD
    ).digest()


def get_signed_message(msg):
    """
    Sign message with random nonce (salt),
    pack into: nonce_len + nonce + sign_len + sign + message_utf8
    and return base64 encoded value
    """
    stamp = int(time.time()).to_bytes(4, 'big')
    nonce = random.getrandbits(NONCE_BYTES*8).to_bytes(NONCE_BYTES, 'big')
    payload = msg.encode('utf-8')
    sign = _signature(stamp, nonce, payload)
    nlen = len(nonce).to_bytes(1, 'big')
    data = b''.join((stamp, nlen, nonce, sign, payload))
    return urlsafe_b64encode(data)


def get_valid_message(msg):
    """
    Cehck and return real message from signed.
    Base64 unencode message,
    unpack from: nonce_len + nonce + sign_len + sign + message_utf8
    and return message
    """
    try:
        data = urlsafe_b64decode(msg)
    except Exception as exc:
        raise ValueError("message data is invalid for b64decode") from exc

    # get message time stamp and check it
    stamp = data[0:4]
    msg_time = int.from_bytes(stamp, 'big')
    time_now = int(time.time())
    if not stamp or msg_time > (time_now + 60*5) or msg_time < (time_now - 60*60*24):
        raise ValueError("message is time is not in range (-1d to +5min)")

    # get nonce, signature and payload
    nlen = data[4] # one byte is int
    if nlen < 4:
        raise ValueError("message nonce is too short")
    nonce = data[5:5+nlen]
    sign = data[5+nlen:5+nlen+HASH_SIZE]
    payload = data[5+nlen+HASH_SIZE:]
    if not nonce or not sign or not payload:
        raise ValueError("some message parts are missing")

    # Calculate signature and test if it's same as in message
    test_sign = _signature(stamp, nonce, payload)
    if test_sign != sign:
        raise ValueError("message signature is not valid")

    # Return accepted payload as string
    return payload.decode('utf-8')
