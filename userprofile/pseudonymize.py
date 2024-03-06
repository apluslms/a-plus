from faker import Faker
import hashlib
import random

from django.contrib.auth.models import User

from userprofile.models import UserProfile

fake = Faker()
num_fakes = 500

fakes = {
    'first_name': [fake.unique.first_name() for _ in range(num_fakes)],
    'last_name': [fake.unique.last_name() for _ in range(num_fakes)],
    'email': [fake.unique.email() for _ in range(num_fakes)],
    'username': [fake.unique.user_name() for _ in range(num_fakes)],
}

def pseudonymize(key: str, data: str):
    hashkey = int(hashlib.md5(data.encode('utf-8')).hexdigest(), 16) % num_fakes
    if key in fakes:
        return fakes[key][hashkey]
    return key

def format_user(user: User, pseudonymized: bool):
    if pseudonymized:
        for _user_profile in UserProfile.objects.all():
            if _user_profile.user == user:
                _user_profile.student_id = random.randint(10000,90000)
        # Return formatted versions of the user's attributes and all the user class's methods
        user.student_id = 99999
        user.first_name = pseudonymize('first_name', user.first_name)
        user.last_name = pseudonymize('last_name', user.last_name)
        user.email = pseudonymize('email', user.email)
        user.username = pseudonymize('username', user.username)
    return user
