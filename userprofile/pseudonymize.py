import json
from random import seed, choice

from faker import Faker
import hashlib

from django.contrib.auth.models import User
from django.contrib.staticfiles import finders

from userprofile.models import UserProfile

fake = Faker(['fi_FI', 'en_US'], use_weighting=False)
num_fakes = 500

fakes = {
    'email': [fake.email() for _ in range(num_fakes)],
    'username': [fake.user_name() for _ in range(num_fakes)],
}

with open(finders.find('../assets/pseudonym.json'), encoding='utf-8') as json_file:
    DATA = json.load(json_file)


def pseudonymize(key: str, data: str):
    hashkey = int(hashlib.sha256(data.encode('utf-8')).hexdigest(), 16) % num_fakes
    if key in fakes:
        return fakes[key][hashkey]
    return key


def format_user(user: User, pseudonymized: bool, user_profile: UserProfile = None):
    if pseudonymized:
        # Return formatted versions of the user's attributes and all the user class's methods
        if user_profile is not None:
            Faker.seed(user_profile.student_id)
            user_profile.student_id = str(fake.random_int(min=10, max=10000))
        seed(user.first_name)
        user.first_name = choice(DATA["colors"])["name"]
        user.last_name = choice(DATA["animals"])
        user.email = pseudonymize('email', user.email)
        user.username = pseudonymize('username', user.username)
    return user
