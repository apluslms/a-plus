from django import forms

from .models import MenuItem


class MenuItemForm(forms.ModelForm):

    class Meta:
        model = MenuItem
        fields = [
            'access',
            'service',
            'menu_url',
            'menu_group_label',
            'menu_label',
            'menu_icon_class',
            'menu_weight',
            'enabled',
        ]
