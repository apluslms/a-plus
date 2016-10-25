import random
import re

from django import forms
from django.conf import settings
from django.core.exceptions import PermissionDenied, ValidationError
from django.forms.utils import ErrorDict
from django.forms.widgets import CheckboxSelectMultiple, RadioSelect, Textarea
from django.utils.safestring import mark_safe
from django.utils.translation import ugettext as _
from util.files import random_ascii
from util.templates import template_to_str
from util import forms as custom_forms
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
        self.show_correct = kwargs.pop('show_correct') if 'show_correct' in kwargs else False
        self.show_correct_once = kwargs.pop('show_correct_once') if 'show_correct_once' in kwargs else False
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

        self.disabled = self.show_correct
        self.randomized = False
        samples = []
        g = 0
        i = 0

        # Travel each fields froup.
        for group in self.exercise["fieldgroups"]:
            if "fields" not in group:
                raise ConfigError("Missing required \"fields\" in field group configuration")

            # Group errors to hide the errorneous fields.
            group_errors = group.get("group_errors", False)
            if group_errors:
                self.group_errors = True

            # Randomly pick fields to include.
            if "pick_randomly" in group:
                self.randomized = True
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
                choices, initial, correct = self.create_choices(field)
                if t == "checkbox":
                    i, f = self.add_field(i, field,
                        forms.MultipleChoiceField, forms.CheckboxSelectMultiple,
                        initial, correct, choices, True, {})
                elif t == "radio":
                    i, f = self.add_field(i, field,
                        forms.ChoiceField, forms.RadioSelect,
                        initial, correct, choices, False, {})
                elif (t == "dropdown" or t == "select"):
                    i, f = self.add_field(i, field,
                        forms.ChoiceField, forms.Select,
                        initial, correct, choices, False)
                elif t == "text":
                    i, f = self.add_field(i, field,
                        forms.CharField, forms.TextInput)
                elif t == "textarea":
                    i, f = self.add_field(i, field,
                        forms.CharField, forms.Textarea)
                elif t == "table-radio":
                    i, f = self.add_table_fields(i, field,
                        forms.ChoiceField, forms.RadioSelect)
                elif t == "table-checkbox":
                    i, f = self.add_table_fields(i, field,
                        forms.MultipleChoiceField, forms.CheckboxSelectMultiple, True)
                elif t == "static":
                    i, f = self.add_field(i, field,
                        forms.CharField, custom_forms.PlainTextWidget)
                else:
                    raise ConfigError("Unknown field type: %s" % (t))

                for fi in f:
                    fi.group_errors = group_errors

                if j == 0:
                    f[0].open_set = self.group_name(g)
                    if "title" in group:
                        f[0].set_title = group["title"]
                if j >= l:
                    f[-1].close_set = True
                j += 1

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

    def add_table_fields(self, i, config, field_class, widget_class, multiple=False):
        fields = []
        choices, initial, correct = self.create_choices(config)
        for row in config.get('rows', []):

            if self.show_correct:
                correct = []
                corr = self.row_options(config, row)['options']
                for i,choice in enumerate(choices):
                    if corr[i]['correct']:
                        correct.append(choice[0])

            row_config = config.copy()
            if 'key' in row:
                row_config['key'] = row['key']
            i, fi = self.add_field(i, row_config,
                field_class, widget_class, initial, correct, choices, multiple, {})
            fi[0].row_label = row.get('label', None)
            fields += fi

            if 'more_text' in config:
                fi[0].more_text = config['more_text']
                more_config = config.copy()
                more_config['key'] = self.field_name(i, row_config) + '_more'
                i, fm = self.add_field(i, more_config,
                    forms.CharField, forms.TextInput)
                fm[0].row_label = row.get('label', None)
                fm[0].table_more = True
                fields += fm

        fields[0].open_table = True
        fields[-1].close_table = True
        return i, fields

    def add_field(self, i, config, field_class, widget_class,
            initial=None, correct=None, choices=None, multiple=False,
            widget_attrs={'class': 'form-control'}):
        args = {
            'widget': widget_class(attrs=widget_attrs),
            'required': 'required' in config and config['required'],
        }
        if self.disabled:
            args['widget'].attrs['disabled'] = 'disabled'
        if not choices is None:
            args['choices'] = choices

        if self.show_correct:
            if correct:
                args['initial'] = correct if multiple else correct[0]
            elif config.get('model', False):
                args['initial'] = config['model']
            elif config.get('correct', False):
                args['initial'] = config['correct']
        else:
            if initial:
                args['initial'] = initial if multiple else initial[0]
            elif config.get('initial', False):
                args['initial'] = config['initial']

        field = field_class(**args)
        field.type = config['type']
        field.name = self.field_name(i, config)
        field.label = mark_safe(config['title'])
        field.more = self.create_more(config)
        field.points = config.get('points', 0)
        field.choice_list = not choices is None and widget_class != forms.Select

        if self.show_correct_once:
            if correct:
                field.correct = correct
            elif config.get('model', False):
                field.correct = config['model']
            elif config.get('correct', False):
                field.correct = config['correct']
                print(field.correct)

        if 'extra_info' in config and 'class' in config['extra_info']:
            field.html_class = config['extra_info']['class']
        else:
            field.html_class = 'form-group'

        self.fields[field.name] = field
        return (i + 1, [field])

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
        initial = []
        correct = []
        if "options" in configuration:
            i = 0
            for opt in configuration["options"]:
                label = opt.get('label', "")
                value = self.option_name(i, opt)
                choices.append((value, mark_safe(label)))
                if opt.get('correct', False):
                    correct.append(value)
                if opt.get('selected', False) or opt.get('initial', False):
                    initial.append(value)
                i += 1
        return choices, initial, correct

    def group_name(self, i):
        return "group_{:d}".format(i)

    def field_name(self, i, config):
        return config.get("key", "field_{:d}".format(i))

    def option_name(self, i, config):
        return config.get("value", "option_{:d}".format(i))

    def append_hint(self, hints, configuration):
        # The old definition of hint per option.
        hint = str(configuration.get('hint', ''))
        if hint and not hint in hints:
            hints.append(hint)

    def bind_initial(self):
        '''
        Binds form using initial values.
        '''
        self.is_bound = True
        self._errors = ErrorDict()
        self.cleaned_data = {}
        for name, field in self.fields.items():
            value = self.initial.get(name, field.initial)
            try:
                self.cleaned_data[name] = field.clean(value)
            except ValidationError as e:
                self.add_error(name, e)
            field.disabled = True

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
                prev = i
                i, ok, p = self.grade_field(i, field)
                points += p
                if not ok:
                    error_fields.append(self.field_name(prev, field))
                    gname = self.group_name(g)
                    if gname not in error_groups:
                        error_groups.append(gname)
            g += 1
        return (points, error_groups, error_fields)

    def compare_values(self, method, val, cmp):
        parts = method.split("-")
        t = parts[0]
        mods = parts[1:]

        if t == "array":
            return cmp in val

        def good_strip(v):
            return v.strip().replace("\r","")
        val = good_strip(val)
        cmp = good_strip(cmp)

        if "ignorerepl" in mods:
            p = re.compile('(^\w+:\s[\w\.\[\]]+\s=)')
            m = p.match(val)
            if m:
                val = val[len(m.group(1)):].strip()

        if "ignorews" in mods or t == "unsortedchars":
            def strip_ws(v):
                return v.replace(" ","")
            val = strip_ws(val)
            cmp = strip_ws(cmp)

        if "ignorequotes" in mods:
            def strip_quotes(v):
                if v.startswith("\"") and v.endswith("\""):
                    return v[1:len(v)-1]
                return v
            val = strip_quotes(val)
            cmp = strip_quotes(cmp)

        if "ignoreparenthesis" in mods:
            def strip_parenthesis(v):
                return v.replace("(","").replace(")","")
            if t == "regexp":
                val = strip_parenthesis(val)
            else:
                val = strip_parenthesis(val)
                cmp = strip_parenthesis(cmp)

        if t == "unsortedchars":
            return set(val) == set(cmp)
        if t == "string":
            if "\n" in cmp:
                cmp_a = [l.strip() for l in cmp.strip().split("\n")]
                val_a = [l.strip() for l in val.strip().split("\n")]
                if len(cmp_a) != len(val_a):
                    return False
                if "requirecase" in mods:
                    return all(c==v for c,v in zip(cmp_a,val_a))
                else:
                    return all(c.lower()==v.lower() for c,v in zip(cmp_a,val_a))
            elif "requirecase" in mods:
                return val == cmp
            else:
                return val.lower() == cmp.lower()
        elif t == "regexp":
            if cmp.startswith('/') and cmp.endswith('/'):
                cmp = cmp[1:-1]
            p = re.compile(cmp)
            return bool(p.search(val))
        elif t == "int":
            try:
                return int(val) == int(cmp)
            except ValueError:
                return False
        elif t == "float":
            try:
                return abs(float(val) - float(cmp)) <= 0.02
            except ValueError:
                return False
        else:
            raise ConfigError("Unknown compare method in form: %s" % (t))

    def grade_field(self, i, configuration):
        t = configuration["type"]

        if t == "table-radio" or t == "table-checkbox":
            all_ok = True
            hints = []
            points = configuration.get("points", 0)
            max_points = points
            first_name = self.field_name(i, configuration)
            for row in configuration.get("rows", []):
                name = self.field_name(i, row)
                value = self.cleaned_data.get(name, None)
                if t == "table-radio":
                    ok, hints, method = self.grade_radio(
                        self.row_options(configuration, row), value, hints)
                else:
                    ok, hints, method = self.grade_checkbox(
                        self.row_options(configuration, row), value, hints)
                if ok:
                    points += row.get("points", 0)
                    max_points += row.get("points", 0)
                else:
                    all_ok = False
                    max_points += row.get("points", 0)
                i += 1
            self.fields[first_name].grade_points = points
            self.fields[first_name].max_points = max_points
            self.fields[name].hints = ' '.join(hints)
            return i, all_ok, points

        name = self.field_name(i, configuration)
        value = self.cleaned_data.get(name, None)
        if t == "checkbox":
            ok, hints, method = self.grade_checkbox(configuration, value)
        elif t == "radio" or t == "dropdown" or t == "select":
            ok, hints, method = self.grade_radio(configuration, value)
        elif t == "text" or t == "textarea":
            ok, hints, method = self.grade_text(configuration, value)
        elif t == "static":
            ok, hints, method = True, [], 'string'
        else:
            raise ConfigError("Unknown field type for grading: %s" % (t))

        # Apply new feedback definitions.
        for fb in configuration.get("feedback", []):
            new_hint = fb.get('label', None)
            comparison = fb.get('value', '')
            if not new_hint:
                continue
            add = False
            if comparison == "%100%":
                add = ok
            else:
                r = self.compare_values(method, value, comparison)
                add = not r if fb.get('not', False) else r
            if add:
                for j in range(len(hints)):
                    if new_hint.startswith(hints[j]):
                        hints[j] = new_hint
                        add = False
                        break
                    elif hints[j].startswith(new_hint):
                        add = False
                        break
            if add:
                hints.append(new_hint)

        points = configuration.get('points', 0)
        self.fields[name].grade_points = points if ok else 0
        self.fields[name].max_points = points
        self.fields[name].hints = hints
        return i + 1, ok, points if ok else 0

    def row_options(self, configuration, row):
        hint = row.get('hint', '')
        correct = row.get('correct_options', [])
        opt = []
        for i, srcopt in enumerate(configuration.get('options', [])):
            trgopt = srcopt.copy()
            trgopt.update({
                'hint': hint,
                'correct': correct[i] if i < len(correct) else False,
            })
            opt.append(trgopt)
        return { 'options': opt }

    def grade_checkbox(self, configuration, value, hints=None):
        hints = hints or []
        correct_count = 0

        # All correct required if any configured
        correct = True
        i = 0
        for opt in configuration.get("options", []):
            name = self.option_name(i, opt)
            if opt.get("correct", False):
                correct_count += 1
                if name not in value:
                    correct = False
                    self.append_hint(hints, opt)
            elif name in value:
                correct = False
                self.append_hint(hints, opt)
            i += 1

        # Add note of multiple correct answers.
        if correct_count > 1 and len(value) == 1:
            hints.append(_("Multiple choices are selectable."))

        return correct_count == 0 or correct, hints, 'array'

    def grade_radio(self, configuration, value, hints=None):
        hints = hints or []
        correct_exists = False

        # One correct required if any configured
        correct = False
        i = 0
        for opt in configuration.get("options", []):
            name = self.option_name(i, opt)
            if opt.get("correct", False):
                correct_exists = True
                if name == value:
                    correct = True
                else:
                    self.append_hint(hints, opt)
            elif name == value:
                self.append_hint(hints, opt)
            i += 1
        return not correct_exists or correct, hints, 'string'

    def grade_text(self, configuration, value, hints=None):
        hints = hints or []
        correct = True
        accept = None
        method = configuration.get('compare_method', 'string')
        if "regex" in configuration:
            accept = configuration["regex"]
            method = "regexp"
        elif "correct" in configuration:
            accept = configuration["correct"]
        if not accept is None:
            correct = self.compare_values(method, value, accept)
        if not correct:
            self.append_hint(hints, configuration)
        return correct, hints, method
