from base64 import urlsafe_b64encode, urlsafe_b64decode
from unittest.mock import patch
from django.test import SimpleTestCase

from lib.crypto.signed_messages import (
    get_signed_message,
    get_valid_message,
    NONCE_BYTES,
    HASH_SIZE,
)


class SignedMessagesTest(SimpleTestCase):
    def setUp(self):
        self.secret = "test secret used for testing only"
        self.message1 = "cat in the tree"
        self.encoded1 = b'AAAAAAQAAAAAJSFeA-4z7Edt2FZjGfwKvO8N011l4xsPQHRVZuwijpFjYXQgaW4gdGhlIHRyZWU='
        self.message2 = "213.8382-234.3847"
        self.encoded2 = b'AAAAAAQAAAAAcXyuQfiAkUPF3HcARt7pRrhP7_T7CJGJO1z85pq8pO4yMTMuODM4Mi0yMzQuMzg0Nw=='

    @patch('time.time', return_value=0)
    @patch('random.getrandbits', return_value=0)
    def test_encrypting_known_messages(self, mock_random, mock_time):
        with self.settings(SECRET_KEY=self.secret):
            encoded1 = get_signed_message(self.message1)
            encoded2 = get_signed_message(self.message2)
        self.assertEqual(encoded1, self.encoded1)
        self.assertEqual(encoded2, self.encoded2)

    @patch('time.time', return_value=0)
    @patch('random.getrandbits', return_value=0)
    def test_decrypting_known_messages(self, mock_random, mock_time):
        with self.settings(SECRET_KEY=self.secret):
            message1 = get_valid_message(self.encoded1)
            message2 = get_valid_message(self.encoded2)
        self.assertEqual(message1, self.message1)
        self.assertEqual(message2, self.message2)

    @patch('time.time', return_value=1000000000)
    @patch('random.getrandbits', return_value=0)
    def test_broken_messages(self, mock_random, mock_time):
        with self.settings(SECRET_KEY=self.secret):
            time = mock_time()
            time_size = 4
            nonce_size = 1+NONCE_BYTES
            sign_size = HASH_SIZE
            header_size = time_size + nonce_size + sign_size

            # get new encoding with corrent time and decode it to raw bytes
            encoded = get_signed_message(self.message1)
            data = urlsafe_b64decode(encoded)

            # test all known errors the library should raise
            no_payload = urlsafe_b64encode(data[:header_size])
            self.assertRaises(ValueError, get_valid_message, no_payload)

            in_future_time = ( time + 60*60*24 ).to_bytes(4, 'big')
            in_future = urlsafe_b64encode(in_future_time + data[time_size:])
            self.assertRaises(ValueError, get_valid_message, in_future)

            in_past_time = ( time - 60*60*24*7 ).to_bytes(4, 'big')
            in_past = urlsafe_b64encode(in_past_time + data[time_size:])
            self.assertRaises(ValueError, get_valid_message, in_past)

            no_nonce = urlsafe_b64encode(data[:time_size] +
                                         (2).to_bytes(1, 'big') +
                                         (0).to_bytes(2, 'big') +
                                         data[time_size+nonce_size:])
            self.assertRaises(ValueError, get_valid_message, no_nonce)

            huge_nonce = urlsafe_b64encode(data[:time_size] +
                                           (250).to_bytes(1, 'big') +
                                           data[time_size+1:])
            self.assertRaises(ValueError, get_valid_message, huge_nonce)

            only_time_and_nonce = urlsafe_b64encode(data[:time_size+nonce_size])
            self.assertRaises(ValueError, get_valid_message, only_time_and_nonce)

            wrong_sign = urlsafe_b64encode(data[:time_size+nonce_size] +
                                           (0).to_bytes(sign_size, 'big') +
                                           data[header_size:])
            self.assertRaises(ValueError, get_valid_message, wrong_sign)

            # test few common errors library should handle
            self.assertRaises(ValueError, get_valid_message, b'')
            self.assertRaises(ValueError, get_valid_message, "string")
            self.assertRaises(ValueError, get_valid_message, b'random \x00 bytes \xff')
