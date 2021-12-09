from typing import Union

from django.contrib.auth.models import AbstractBaseUser, AnonymousUser


AnyUser = Union[AbstractBaseUser, AnonymousUser]
