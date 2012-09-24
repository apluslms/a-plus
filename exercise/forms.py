from django import forms
from exercise.submission_models import Submission
from exercise.exercise_models import BaseExercise
from django.utils.translation import ugettext_lazy as _

class SubmissionReviewForm(forms.Form):
    points          = forms.IntegerField(min_value=0)
    feedback        = forms.CharField(required=False, 
                                      widget=forms.Textarea,
                                      help_text=_("HTML formatting is allowed"))
    
    def clean(self):
        points      = self.cleaned_data.get("points")
        max_points  = self.cleaned_data.get("max_points")
        
        if points and max_points:
            if points > max_points:
                raise forms.ValidationError("Points greater than maximum points are not allowed.")
        
            if points < 0:
                raise forms.ValidationError("Points lower than zero are not allowed.")
        
        return self.cleaned_data

class SubmissionCallbackForm(forms.Form):
    points          = forms.IntegerField(min_value=0)
    max_points      = forms.IntegerField(min_value=0)
    
    feedback        = forms.CharField(required=False)
    grading_payload = forms.CharField(required=False)
    
    def clean(self):
        points      = self.cleaned_data.get("points")
        max_points  = self.cleaned_data.get("max_points")
        
        if points and max_points:
            if points > max_points:
                raise forms.ValidationError("Points greater than maximum points are not allowed.")
        
            if points < 0:
                raise forms.ValidationError("Points lower than zero are not allowed.")
        
        return self.cleaned_data

class BaseExerciseForm(forms.ModelForm):
    class Meta:
        model = BaseExercise
        exclude = ("order", "course_module")
    
    def get_fieldsets(self):
        return [{"legend": _("Exercise"), "fields": self.get_exercise_fields()},
                {"legend": _("Grading"), "fields": self.get_grading_fields()},
                {"legend": _("Groups"), "fields": self.get_group_fields()},
                ]
    
    def get_exercise_fields(self):
        return (self["name"], 
                self["description"])
    
    def get_grading_fields(self):
        return (self["max_submissions"],
                self["max_points"],
                self["points_to_pass"],
                self["allow_assistant_grading"])
    
    def get_group_fields(self):
        return (self["min_group_size"],
                self["max_group_size"])