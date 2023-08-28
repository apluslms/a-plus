from copy import deepcopy
from datetime import timedelta
import itertools
import logging
from typing import Any, Iterable, List, Optional, Union, Tuple

from django.test import TestCase
from django.utils import timezone

from .configure import configure, parse_bool
from course.models import Course, CourseInstance, CourseModule, LearningObjectCategory
from exercise.models import LearningObject, CourseChapter, BaseExercise, LTIExercise
from external_services.models import LTIService


logger = logging.getLogger("test")

configs = [
    {
        "categories": {
            "cat1": {
                "name": "category1",
            },
            "cat2": {
                "name": "category2",
            },
        },
        "modules": [
            {
                "key": "module1",
            },
            {
                "key": "module2",
            },
        ],
    },
]

module_configs = [
    {}
]

exercise_configs = {
    "LTIExercise": [
        {
            "lti": "lti",
            "category": "cat1",
            "title": "test_title",
        }
    ],
    "BaseExercise": [
        {
            "max_submissions": 3,
            "category": "cat1",
            "title": "test_title",
        }
    ],
    "CourseChapter": [
        {
            "category": "cat1",
            "title": "test_title",
        }
    ],
}

category_configs = {
    "cat1": {
        "name": "category1",
    },
    "cat2": {
        "name": "category2",
    },
    "cat3": {
        "name": "cat3",
        "accept_unofficial_submits": True,
    },
}

class ConfigureTest(TestCase):
    course: Course
    instance: CourseInstance
    config: dict

    def setUp(self):
        self.config = configs[0]

        self.course = Course.objects.create(
            name="test course",
            code="123456",
            url="Course-Url"
        )

        self.today = timezone.now()
        self.yesterday = self.today - timedelta(days=1)
        self.tomorrow = self.today + timedelta(days=1)
        self.two_days_from_now = self.tomorrow + timedelta(days=1)
        self.three_days_from_now = self.two_days_from_now + timedelta(days=1)

        self.instance = CourseInstance.objects.create(
            instance_name="Fall 2011 day 1",
            enrollment_starting_time=self.yesterday,
            starting_time=self.today,
            ending_time=self.tomorrow,
            course=self.course,
            url="T-00.1000_d1",
            view_content_to=CourseInstance.VIEW_ACCESS.ENROLLMENT_AUDIENCE,
        )

        self.lti_service = LTIService.objects.create(
            url='http://localhost:8080/lti-launch', # fake URL
            consumer_key='apluskey',
            consumer_secret='aplussecret',
            menu_label="lti",
            access_settings=LTIService.LTI_ACCESS.ANON_API_NO,
        )

        self.module_field_map = {
            "key": "url",
            "title": "name",
            "children": None,
        }
        self.lobject_field_map = {
            "key": "url",
            "url": "service_url",
            "title": "name",
            "children": None,
            "category": ("category", self.get_category_by_key),
            "target_category": ("target_category", self.get_category_by_name),
            "lti": ("lti_service", self.get_lti_service),
            "target_url": None,
        }
        self.category_field_map = {}

    def tearDown(self) -> None:
        self.instance.course_modules.all().delete()
        self.instance.delete()
        self.course.delete()

    def test_modules(self):
        self.configure_and_test()

        self.insert_module(
            self.config,
            self.get_module_config(0, "test_module"),
        )
        self.insert_module(
            self.config,
            self.get_module_config(0, "test_order_change"),
            0,
        )

        self.configure_and_test()

        self.remove_module(self.config, (1,2))

        self.configure_and_test()

    def test_exercises(self):
        self.insert_exercise(
            self.config,
            self.get_exercise_config("BaseExercise", 0, "test_BaseExercise"),
            0,
        )
        self.insert_exercise(
            self.config,
            self.get_exercise_config("LTIExercise", 0, "test_LTIExercise"),
            0,
        )
        self.insert_exercise(
            self.config,
            self.get_exercise_config("CourseChapter", 0, "test_CourseChapter"),
            0,
        )
        self.insert_exercise(
            self.config,
            self.get_exercise_config("BaseExercise", 0, "test_nested_BaseExercise"),
            0,
            [2],
        )

        self.configure_and_test()

        self.insert_exercise(
            self.config,
            self.get_exercise_config("CourseChapter", 0, "test_replace_BaseExercise"),
            0,
            [2],
            replace=True,
        )

        self.configure_and_test()

        self.remove_exercise(
            self.config,
            0,
            [],
            (0,4),
        )

        self.configure_and_test()

    def test_changing_type(self):
        exercise_types = set(exercise_configs.keys())
        # test every pair of exercise types
        for a, b in itertools.product(exercise_types, exercise_types):
            if a == b:
                continue

            self.insert_exercise(
                self.config,
                self.get_exercise_config(a, 0, "test_TypeChange"),
                0,
            )

            self.configure_and_test()

            self.remove_exercise(
                self.config,
                0,
            )

            self.insert_exercise(
                self.config,
                self.get_exercise_config(b, 0, "test_TypeChange"),
                0,
            )

            self.configure_and_test()

            self.remove_exercise(
                self.config,
                0,
            )

    def test_field_defined_by_dict(self):
        exercise_config = self.get_exercise_config("BaseExercise", 0, "test_BaseExercise")

        exercise_config["exercise_info"] = {
            "test": "test",
            "test2": "test2",
        }
        self.insert_exercise(self.config, exercise_config, 0)
        self.configure_and_test()

        exercise_config["exercise_info"] = {
            "test": "test",
            "test2": "test2",
            "test3": "test3",
        }
        self.insert_exercise(self.config, exercise_config, 0)
        self.configure_and_test()

        exercise_config["exercise_info"] = {
            "test": "test",
        }
        self.insert_exercise(self.config, exercise_config, 0)
        self.configure_and_test()

        exercise_config["exercise_info"] = {
            "test5": "test5",
        }
        self.insert_exercise(self.config, exercise_config, 0)
        self.configure_and_test()

    def test_categories(self):
        self.set_category(self.config, "cat3", category_configs["cat3"])

        self.configure_and_test()

        self.remove_category(self.config, "cat2")

        self.configure_and_test()

        self.set_category(self.config, "cat1", category_configs["cat2"])

        self.configure_and_test()

    def configure_and_test(self):
        success, errors = configure(self.instance, self.config)
        for e in errors:
            logger.error(e)
        self.assertTrue(success)
        self.assertTrue(not errors)
        self.check_instance_config(self.instance, self.config)


    def check_categories_config(self, categories: Iterable[LearningObjectCategory], config: dict):
        # Hidden categories are old, so skip them
        categories = [
            category
            for category in categories
            if category.status != LearningObjectCategory.STATUS.HIDDEN
        ]
        category_names = {category.name for category in categories}
        name_to_category_config = {c["name"]: c for c in config.values()}
        config_category_names = set(name_to_category_config.keys())

        self.assertEqual(category_names, config_category_names)

        for category in categories:
            self.check_fields(self.category_field_map, category, name_to_category_config[category.name])


    def check_lobject_config(self, lobject: LearningObject, config: dict):
        # order should be set by check_instance_config
        self.assertTrue("order" in config)

        self.check_fields(self.lobject_field_map, lobject, config)

        lobject_cls = (
            LTIExercise if "lti" in config
            else BaseExercise if "max_submissions" in config
            else CourseChapter
        )

        self.assertEqual(type(lobject), lobject_cls)

        lobjects = {c["key"]: c for c in config.get("children", [])}
        self.assertEqual(set(lobjects.keys()), set(lobj.url for lobj in lobject.children.all()))

        for lobj in lobject.children.all():
            o = lobjects[lobj.url]
            self.check_lobject_config(lobj, o)

    def check_module_config(self, module: CourseModule, config: dict):
        # order should be set by check_instance_config
        self.assertTrue("order" in config)

        self.check_fields(self.module_field_map, module, config)

        children = module.learning_objects.filter(parent=None).all()

        lobjects = {c["key"]: c for c in config.get("children", [])}
        self.assertEqual(set(lobjects.keys()), set(lobject.url for lobject in children))

        for lobject in children:
            o = lobjects[lobject.url]
            self.check_lobject_config(lobject, o)

    def check_instance_config(self, instance: CourseInstance, config: dict):
        def set_order(config, n = 0) -> int:
            for o in config.get("children", []):
                if "order" not in o:
                    n += 1
                    o["order"] = n

                set_order(o)
            return n

        config = deepcopy(config)

        modules = {c["key"]: c for c in config.get("modules", [])}
        self.assertEqual(set(modules.keys()), set(module.url for module in instance.course_modules.all()))

        self.check_categories_config(instance.categories.all(), config["categories"])

        n = 0
        nn = 0
        for o in config.get("modules", []):
            if "order" not in o:
                n += 1
                o["order"] = n

            if not ("numerate_ignoring_modules" in config \
                    and parse_bool(config["numerate_ignoring_modules"])):
                nn = 0

            nn = set_order(o, nn)

        for module in instance.course_modules.all():
            m = modules[module.url]

            self.check_module_config(module, m)

    def check_fields(self, mapping: dict, obj: Any, config: dict) -> None:
        for key, value in config.items():
            key = mapping.get(key, key)
            if key is None:
                continue

            if isinstance(key, tuple):
                key, func = key
                value = func(value)

            self.assertEqual(getattr(obj, key), value, f"attr: {key}")

    def get_module_config(self, index, key):
        ret = deepcopy(module_configs[index])
        values = {
            "key": key,
        }

        ret.update(values)
        return ret

    def get_exercise_config(self, typ, index, key):
        ret = deepcopy(exercise_configs[typ][index])
        values = {
            "key": key,
        }

        ret.update(values)
        return ret

    def insert_module(
            self,
            config: dict,
            module_config: dict,
            index: Optional[int] = None
            ) -> None:
        config.setdefault("modules", [])
        if index is None:
            config["modules"].append(module_config)
        else:
            config["modules"].insert(index, module_config)

    def remove_module(
            self,
            config: dict,
            index: Optional[Union[int, Tuple[int, int]]] = None,
            ) -> None:
        if index is None:
            config["modules"].pop()
        elif isinstance(index, tuple):
            del config["modules"][index[0]:index[1]]
        else:
            del config["modules"][index]

    def insert_exercise( # pylint: disable=too-many-arguments
            self,
            config: dict,
            lobject_config: dict,
            module_index: int,
            indices: Optional[List[int]] = None,
            index: Optional[int] = None,
            replace: bool = False,
            ) -> None:
        if indices is None:
            indices = []

        parent = config["modules"][module_index]
        for i in indices:
            parent = parent["children"][i]

        parent.setdefault("children", [])

        if replace:
            if index is None:
                parent["children"].pop()
            else:
                del parent["children"][index]

        if index is None:
            parent["children"].append(lobject_config)
        else:
            parent["children"].insert(index, lobject_config)

    def remove_exercise(
            self,
            config: dict,
            module_index: int,
            indices: Optional[List[int]] = None,
            index: Optional[Union[int, Tuple[int, int]]] = None,
            ) -> None:
        """Remove exercise from the <config>

        :param indices: a list of child indices to access the correct chapter. If the
        exercise to be removed is at the top-level of the module, leave empty. If
        it is under a chapter that is at the top-level of the module, include the
        index of the chapter in the module.
        :param index: the index of the exercise to be removed. Can be a tuple to
        indicate a range of indices, or None to remove the last exercise.
        """
        if indices is None:
            indices = []

        parent = config["modules"][module_index]
        for i in indices:
            parent = parent["children"][i]

        if index is None:
            parent["children"].pop()
        elif isinstance(index, tuple):
            del parent["children"][index[0]:index[1]]
        else:
            del parent["children"][index]

    def set_category(
            self,
            config: dict,
            category_key: str,
            category_config: dict,
            ) -> None:
        config["categories"][category_key] = category_config

    def remove_category(
            self,
            config: dict,
            category_key: str,
            ) -> None:
        del config["categories"][category_key]

    def get_category_by_key(self, category_key):
        return self.instance.categories.get(name=self.config["categories"][category_key]["name"])

    def get_category_by_name(self, category_name):
        return self.instance.categories.get(name=category_name)

    def get_lti_service(self, lti_key):
        return LTIService.objects.get(menu_label=lti_key)
