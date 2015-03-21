# Django
from django.test import TestCase
from django.test.client import Client
from django.contrib.auth.models import User

# Aalto+
from course.models import *

# Python
from datetime import datetime, timedelta

class CourseTest(TestCase):
    def setUp(self):
        self.client = Client()
        
        now = datetime.now()
        tomorrow = now + timedelta(days=365)
        
        self.course = Course.objects.create(name="test course", 
                                            code="123456",
                                            url="Course-Url")
        
        self.course_instance = CourseInstance.objects.create(instance_name="Fall 2011", 
                                                             website="http://www.example.com", 
                                                             starting_time=now,
                                                             ending_time=tomorrow,
                                                             course=self.course,
                                                             url="T-00.1000"
                                                             )
    
    def test_course_open(self):
        # Get an old instance model
        old_instance = CourseInstance.objects.get(pk=1)
        self.assertTrue(self.course_instance.is_open())
        
        future_instance = CourseInstance(instance_name="Fall 2011", 
                                         website="http://www.example.com", 
                                         starting_time=datetime.now()+timedelta(days=1),
                                         ending_time=datetime.now()+timedelta(days=365),
                                         )
        self.assertFalse(future_instance.is_open())
    
    def test_course_url(self):
        self.assertTrue(self.course_instance.url in self.course_instance.get_absolute_url())
        self.assertTrue(self.course_instance.course.url in self.course_instance.get_absolute_url())
    
    def test_course_staff(self):
        user = User(username="test_abc")
        user.set_password("asdfgh1234")
        user.save()
        
        self.assertFalse(user.userprofile in self.course_instance.get_course_staff())
        self.course_instance.assistants.add(user.userprofile)
        self.assertTrue(user.userprofile in self.course_instance.get_course_staff())
        self.course_instance.assistants.clear()
        self.assertFalse(user.userprofile in self.course_instance.get_course_staff())
        self.course.teachers.add(user.userprofile)
        self.assertTrue(user.userprofile in self.course_instance.get_course_staff())
    
    def test_course_views(self):
        # Test viewing a course without logging in
        response = self.client.get(self.course.get_absolute_url())
        self.assertEqual(302, response.status_code)
        
        response = self.client.get(self.course_instance.get_absolute_url())
        self.assertEqual(302, response.status_code)
        
        # Login
        user = User(username="student")
        user.set_password("student")
        user.save()
        
        self.client.login(username="student", password="student")
        
        response = self.client.get(self.course.get_absolute_url())
        self.assertEqual(200, response.status_code)
        
        response = self.client.get(self.course_instance.get_absolute_url())
        self.assertEqual(200, response.status_code)
