from typing import Optional

from django.test import SimpleTestCase
from django.http import HttpResponse

from .request_globals import RequestGlobal


class TestGlobal(RequestGlobal):
    test = None
    def init(self):
        self.test = "test"


class PassthroughMiddleware:
    def __call__(self, _request):
        return


def capture_test_global(_get_response):
    def inner(_request):
        request_global_test_obj.obj = TestGlobal()
        return HttpResponse()
    return inner


request_global_test_obj = None
class RequestGlobalTest(SimpleTestCase):
    obj: Optional[TestGlobal]

    def setUp(self) -> None:
        global request_global_test_obj
        RequestGlobal.clear_globals()
        request_global_test_obj = self

    def test_clear_globals(self):
        obj = TestGlobal()
        RequestGlobal.clear_globals()
        obj2 = TestGlobal()
        self.assertIsNot(obj, obj2)

    def test_returns_same_object(self):
        obj = TestGlobal()
        self.assertIsInstance(obj, TestGlobal)
        obj2 = TestGlobal()
        self.assertIs(obj, obj2)
        obj3 = TestGlobal()
        self.assertIs(obj, obj3)

    def test_is_request_specific(self):
        with self.modify_settings(MIDDLEWARE={"append": ["lib.tests.capture_test_global"]}):
            obj2 = TestGlobal()
            self.client.get("/")
            self.assertIsInstance(self.obj, TestGlobal)
            obj2 = self.obj
            self.client.get("/")
            self.assertIsInstance(self.obj, TestGlobal)
            self.assertIsNot(self.obj, obj2)

    def test_is_cleared_at_the_end(self):
        with self.modify_settings(MIDDLEWARE={"append": ["lib.tests.capture_test_global"]}):
            self.client.get("/")
            obj2 = TestGlobal()
            self.assertIsInstance(self.obj, TestGlobal)
            self.assertIsInstance(obj2, TestGlobal)
            self.assertIsNot(self.obj, obj2)

    def test_init_called(self):
        obj = TestGlobal()
        self.assertEqual(obj.test, "test")
