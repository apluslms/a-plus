# Copyright 2010 VPAC
#
# This file is part of django_shibboleth.
#
# django_shibboleth is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# django_shibboleth is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with django_shibboleth  If not, see <http://www.gnu.org/licenses/>.

from django import forms
from django.conf import settings
from django.contrib.auth.models import User

class BaseRegisterForm(forms.Form):    

    def save(self, attr):
        user = User.objects.create_user(attr[settings.SHIB_USERNAME], attr[settings.SHIB_EMAIL], '')
        return user
