import random
import re

from django import forms
from django.conf import settings
from django.core.exceptions import PermissionDenied
from django.forms.widgets import CheckboxSelectMultiple, RadioSelect, Textarea
from django.utils.safestring import mark_safe
from util.files import random_ascii
from util.templates import template_to_str
from .auth import make_hash
from ..config import ConfigError


class GradedForm(forms.Form):
    '''
    A dynamically build form class for an exercise.

    '''

    def __init__(self, *args, **kwargs):
        '''
        Constructor. Requires keyword argument "exercise".

        '''
        if "exercise" not in kwargs:
            raise ConfigError("Missing exercise configuration from form arguments.")
        self.exercise = kwargs.pop("exercise")
        kwargs['label_suffix'] = ''
        super(forms.Form, self).__init__(*args, **kwargs)
        if "fieldgroups" not in self.exercise:
            raise ConfigError("Missing required \"fieldgroups\" in exercise configuration")

        # Check that sample is unmodified in a randomized form.
        if not args[0] is None:
            nonce = args[0].get('_nonce', '')
            sample = args[0].get('_sample', '')
            if nonce and sample:
                if self.samples_hash(nonce, sample) != args[0].get('_checksum', ''):
                    raise PermissionDenied('Invalid checksum')
                post_samples = sample.split('/')

        self.disabled = False
        samples = []
        g = 0
        i = 0

        # Travel each fields froup.
        for group in self.exercise["fieldgroups"]:
            if "fields" not in group:
                raise ConfigError("Missing required \"fields\" in field group configuration")

            # Randomly pick fields to include.
            if "pick_randomly" in group:
                if not args[0] is None:
                    self.disabled = True
                    if len(post_samples) > 0:
                        indexes = [int(i) for i in post_samples.pop(0).split('-')]
                    else:
                        indexes = []
                else:
                    indexes = random.sample(range(len(group["fields"])), int(group["pick_randomly"]))
                    samples.append('-'.join([str(i) for i in indexes]))
                group["_fields"] = [group["fields"][i] for i in indexes]
            else:
                group["_fields"] = group["fields"]

            j = 0
            l = len(group["_fields"]) - 1

            # Travel each field in group.
            for field in group["_fields"]:
                if "type" not in field:
                    raise ConfigError("Missing required \"type\" in field configuration for: %s" % (group["name"]))
                t = field["type"]

                # Create a field by type.
                f = None
                r = "required" in field and field["required"]
                atr = {"class": "form-control", "readonly": self.disabled}
                if t == "checkbox":
                    f = forms.MultipleChoiceField(widget=forms.CheckboxSelectMultiple(),
                        required=r, choices=self.create_choices(field))
                elif t == "radio":
                    f = forms.ChoiceField(widget=forms.RadioSelect(), required=r,
                        choices=self.create_choices(field))
                elif t == 'dropdown':
                    f = forms.ChoiceField(widget=forms.Select(attrs=atr), required=r,
                        choices=self.create_choices(field))
                elif t == "text":
                    f = forms.CharField(widget=forms.TextInput(attrs=atr), required=r)
                elif t == "textarea":
                    f = forms.CharField(widget=forms.Textarea(attrs=atr), required=r)
                else:
                    raise ConfigError("Unknown field type: %s" % (t))
                f.type = t
                f.choice_list = (t == "checkbox" or t == "radio")

                # Set field defaults.
                f.label = mark_safe(field["title"])
                f.more = self.create_more(field)
                if j == 0:
                    f.open_set = self.group_name(g)
                    if "title" in group:
                        f.set_title = group["title"]
                if j >= l:
                    f.close_set = True
                j += 1

                # Store field in form.
                self.fields[self.field_name(i)] = f
                i += 1
            g += 1

        # Protect sample used in a randomized form.
        if len(samples) > 0:
            self.nonce = random_ascii(16)
            self.sample = '/'.join(samples)
            self.checksum = self.samples_hash(self.nonce, self.sample)


    def samples_hash(self, nonce, sample):
        return make_hash(
            self.exercise.get('secret') or settings.AJAX_KEY,
            nonce + sample
        )


    def create_more(self, configuration):
        '''
        Creates more instructions by configuration.

        '''
        more = ""
        if "more" in configuration:
            more += configuration["more"]
        if "include" in configuration:
            more += template_to_str(None, None, configuration["include"])
        return more or None


    def create_choices(self, configuration):
        '''
        Creates field choices by configuration.

        '''
        choices = []
        if "options" in configuration:
            i = 0
            for opt in configuration["options"]:
                label = ""
                if "label" in opt:
                    label = opt["label"]
                choices.append((self.option_name(i), mark_safe(label)))
                i += 1
        return choices


    def group_name(self, i):
        return "group_%d" % (i)


    def field_name(self, i):
        return "field_%d" % (i)


    def option_name(self, i):
        return "option_%d" % (i)


    def append_hint(self, hints, configuration):
        if 'hint' in configuration and not configuration['hint'] in hints:
            hints.append(str(configuration['hint']))


    def grade(self):
        '''
        Grades form answers.

        '''
        points = 0
        error_fields = []
        error_groups = []
        g = 0
        i = 0
        for group in self.exercise["fieldgroups"]:
            for field in group["_fields"]:
                name = self.field_name(i)
                val = self.cleaned_data.get(name, None)
                ok, hints = self.grade_field(field, val)
                if ok:
                    if "points" in field:
                        points += field["points"]
                else:
                    self.fields[name].hints = ' '.join(hints)
                    error_fields.append(name)
                    gname = self.group_name(g)
                    if gname not in error_groups:
                        error_groups.append(gname)
                i += 1
            g += 1
        return (points, error_groups, error_fields)


    def grade_field(self, configuration, value):
        '''
        Grades field answer.

        '''
        t = configuration["type"]

        # Grade checkbox: all correct required if any configured
        if t == "checkbox":
            i = 0
            correct_exists = False
            correct = True
            hints = []
            for opt in configuration["options"]:
                name = self.option_name(i)
                if "correct" in opt and opt["correct"]:
                    correct_exists = True
                    if name not in value:
                        correct = False
                        self.append_hint(hints, opt)
                elif name in value:
                    correct = False
                    self.append_hint(hints, opt)
                i += 1
            return not correct_exists or correct, hints

        # Grade radio: correct required if any configured
        elif t == "radio" or t == "dropdown":
            i = 0
            correct = True
            hints = []
            for opt in configuration["options"]:
                name = self.option_name(i)
                if "correct" in opt and opt["correct"]:
                    if name != value:
                        correct = False
                        self.append_hint(hints, opt)
                elif name == value:
                    self.append_hint(hints, opt)
                i += 1
            return correct, hints

        # Grade text: correct text required if configured
        elif t == "text" or t == "textarea":
            correct = True
            hints = []
            if "correct" in configuration:
                correct = value.strip() == configuration["correct"]
            elif "regex" in configuration:
                p = re.compile(configuration["regex"])
                correct = p.match(value.strip()) != None
            if not correct:
                self.append_hint(hints, configuration)
            return correct, hints

        raise ConfigError("Unknown field type for grading: %s" % (configuration["type"]))
