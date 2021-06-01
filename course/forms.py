from django import forms
from django.contrib.humanize.templatetags.humanize import ordinal
from django.utils.safestring import mark_safe
from django.utils.translation import gettext_lazy as _

from aplus.api import api_reverse
from lib.fields import UsersSearchSelectField
from .models import Enrollment, StudentGroup
from userprofile.models import UserProfile


class GroupsForm(forms.Form):

    def __init__(self, *args, **kwargs):
        self.profile = kwargs.pop('profile')
        self.instance = kwargs.pop('instance')
        self.content = kwargs.pop('content')
        super().__init__(*args, **kwargs)
        total = self.content.total()
        min_size = max(total['min_group_size'], 2)
        max_size = total['max_group_size']

        for n in range(2, max_size + 1):
            widget = forms.TextInput(attrs={'class':'form-control'})
            field = forms.CharField(widget=widget, required=(n <= min_size))
            field.label = mark_safe(_('GROUP_MEMBER_LABEL -- {num}').format(num=ordinal(n)))
            self.fields['member{:d}'.format(n)] = field

    def clean(self):
        super().clean()

        self.member_profiles = [self.profile]
        for key in self.fields.keys():
            if key in self.cleaned_data and self.cleaned_data[key]:
                enrollment = Enrollment.objects.filter(
                    course_instance=self.instance,
                    personal_code=self.cleaned_data[key].upper()
                ).first()
                if not enrollment:
                    self.add_error(key, _('ERROR_CODE_NOT_RECOGNIZED'))
                elif enrollment.user_profile in self.member_profiles:
                    self.add_error(key, _('ERROR_USER_ALREADY_IN_GROUP'))
                else:
                    self.member_profiles.append(enrollment.user_profile)

        if not self.errors and len(self.member_profiles) > 1:
            if StudentGroup.get_exact(self.instance, self.member_profiles):
                self.add_error(None, _('ERROR_GROUP_ALREADY_EXISTS'))

        return self.cleaned_data

    def save(self):
        group = StudentGroup(course_instance=self.instance)
        group.save()
        group.members.add(*self.member_profiles)
        return group


class GroupSelectForm(forms.Form):
    group = forms.IntegerField(required=True)

    def __init__(self, *args, **kwargs):
        self.profile = kwargs.pop('profile')
        self.instance = kwargs.pop('instance')
        super().__init__(*args, **kwargs)

    def clean(self):
        super().clean()
        self.selected_group = None
        if 'group' in self.cleaned_data:
            gid = self.cleaned_data['group']
            if gid != 0:
                group = self.profile.groups.filter(id=gid, course_instance=self.instance).first()
                if group:
                    self.selected_group = group
                else:
                    self.add_error('group', 'Invalid group id')
        return self.cleaned_data

    def save(self):
        enrollment = self.instance.get_enrollment_for(self.profile.user)
        enrollment.selected_group = self.selected_group
        enrollment.save()
        return enrollment


class GroupEditForm(forms.ModelForm):

    members = UsersSearchSelectField(queryset=UserProfile.objects.none(),
        initial_queryset=UserProfile.objects.none())

    def __init__(self, *args, **kwargs):
        course_instance = kwargs.get('instance').course_instance
        super().__init__(*args, **kwargs)
        self.fields['members'].widget.attrs["data-search-api-url"] = api_reverse(
            "course-students-list", kwargs={'course_id': course_instance.id})
        self.fields["members"].queryset = course_instance.get_student_profiles()
        # Course staff may use this form for modifying and creating student groups.
        # If an existing group is being modified, its current members must be
        # set to the initial queryset.
        if self.instance.id:
            self.fields["members"].initial_queryset = self.instance.members.all()

    class Meta:
        model = StudentGroup
        fields = ['members']


class EnrollStudentsForm(forms.Form):

    user_profiles = UsersSearchSelectField(queryset=UserProfile.objects.all(),
        initial_queryset=UserProfile.objects.none(),
        label=_('USERS'))

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['user_profiles'].widget.attrs["data-search-api-url"] = api_reverse(
            "user-list")
