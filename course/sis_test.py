import json
import logging
from typing import List, Tuple
from django.conf import settings
from course.sis import StudentInfoSystem

logger = logging.getLogger('aplus.course')

origdata = [
    {
        "code": "TEST-A1111",
        "id": "1",
        "instance": "spring-2022",
        "starting_time": "2022-01-13",
        "ending_time": "2022-05-04",
        "teachers": [ "teacher-A", "teacher-C" ],
        "participants": [ "222222", "333333", "555555" ],
    },
    {
        "code": "TEST-A1111",
        "id": "2",
        "instance": "summer-2022",
        "starting_time": "2022-06-04",
        "ending_time": "2022-07-30",
        "teachers": [ "teacher-B" ],
        "participants": [ "444444", "555555", "333333" ],
    },
    {
        "code": "123456",
        "id": "123",
        "instance": "summer-2022",
        "starting_time": "2022-06-01",
        "ending_time": "2022-08-20",
        "teachers": [ "teacher-A", "testTeacher" ],
        "participants": [ "123TEST", "333333", "555555" ],
    },
]

class SisTest(StudentInfoSystem):
    '''
    This SIS class can be used for testing the SIS functions. It can be taken into use
    by adding the following to settings.py:

    SIS_PLUGIN_MODULE = 'course.sis_test'
    SIS_PLUGIN_CLASS = 'SisTest'

    By using optional SIS_TEST_FILE setting, one can specify a file from which the SIS
    configuration is read, overriding the default setup above.
    '''

    def __init__(self):
        self.data = origdata
        if hasattr(settings, 'SIS_TEST_FILE'):
            try:
                with open(settings.SIS_TEST_FILE, "r", encoding="utf-8") as f:
                    self.data = json.load(f)
            except Exception:
                logger.exception("File read error.")

    def get_instances(self, course: str) -> List[Tuple[str, str]]:
        selected = list(filter(lambda d: d['code'] == course, self.data))
        ret = list(map(lambda k: (k['id'], k['instance']), selected))
        return ret

    def get_course_data(self, id: str) -> dict: # pylint: disable=redefined-builtin
        selected = next(filter(lambda d: d['id'] == id, self.data), None)
        return selected

    def get_participants(self, id: str) -> List[str]: # pylint: disable=redefined-builtin
        selected = next(filter(lambda d: d['id'] == id, self.data), None)
        if selected:
            return selected['participants']
        return []