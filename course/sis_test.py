from typing import List, Tuple
from course.sis import StudentInfoSystem

data = [
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
    '''

    def get_instances(self, course: str) -> List[Tuple[str, str]]:
        selected = list(filter(lambda d: d['code'] == course, data))
        ret = list(map(lambda k: (k['id'], k['instance']), selected))
        return ret

    def get_course_data(self, id: str) -> dict:
        selected = next(filter(lambda d: d['id'] == id, data), None)
        return selected

    def get_participants(self, id: str) -> List[str]:
        selected = next(filter(lambda d: d['id'] == id, data), None)
        if selected:
            return selected['participants']
        else:
            return []