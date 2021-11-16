from typing import Dict, List, Optional, cast

from bs4 import BeautifulSoup
from bs4.element import NavigableString, Tag

class ExercisePage:
    """
    Represents the pages that are received from exercise services as objects.
    The pages have both submission related fields, such as 'is_graded' and
    'points', as well as meta information such as 'title' and 'description'.
    """
    def __init__(self, exercise):
        self.exercise = exercise
        self.is_loaded = False
        self.is_graded = False
        self.is_accepted = False
        self.is_rejected = False
        self.is_wait = False
        self.points = 0
        self.max_points = exercise.max_points \
            if hasattr(exercise, 'max_points') else 0
        self.head = ""
        self.content = ""
        self.clean_content = ""
        self.last_modified = ""
        self.expires = 0
        self.meta = {
            "title": exercise.name,
            "description": exercise.description
        }
        self.errors = []

    def is_sane(self):
        """
        Checks that the values are sane/acceptable.
        """
        return self.points <= self.max_points
            # and not (self.exercise.max_points != 0 \
            #         and self.max_points == 0)

    def populate_form(
            self,
            field_values: Optional[Dict[str, List[str]]] = None,
            data_values: Optional[Dict[str, str]] = None,
            allow_submit: bool = True,
        ) -> None:
        """
        Populates the provided values into the exercise form by manipulating
        its HTML. `field_values` are inserted into the form input fields.
        `data_values` are inserted into `data` attributes in the form element.
        If `allow_submit` is `False`, the submit button is hidden.
        """
        soup = BeautifulSoup(self.content, 'html5lib')

        exercise_element = self._find_exercise_element(soup)
        if exercise_element is None:
            return

        # Most likely there is only one form
        for form_element in exercise_element.find_all('form'):
            if field_values is not None:
                self._populate_fields(form_element, field_values)
            if data_values is not None:
                self._populate_data(form_element, data_values)
            if not allow_submit:
                self._remove_submit_button(form_element)
        self.content = str(exercise_element)

    def _find_exercise_element(self, soup: BeautifulSoup) -> Optional[Tag]:
        """
        Finds the element that contains the exercise content. Returns `None` if
        not found.
        """
        # The exercise content element may be identified by a number of
        # different ids or classes
        exercise_element = soup.find(id=['exercise', 'aplus', 'chapter'])
        if not isinstance(exercise_element, Tag):
            exercise_element = soup.find({'class': 'entry-content'})
        if not isinstance(exercise_element, Tag):
            exercise_element = soup.body

        return exercise_element

    def _populate_fields(self, form_element: Tag, field_values: Dict[str, List[str]]) -> None:
        """
        Inserts the provided values into the form input elements inside the
        exercise element.
        """
        # Find all form elements on the exercise page and fill in the values
        field_elements = form_element.find_all(['input', 'select', 'textarea'])
        for field_element in field_elements:
            field_element = cast(Tag, field_element)
            field_name = cast(str, field_element.get('name'))
            if field_name not in field_values:
                continue
            if field_element.name == 'input':
                if field_element.get('type') in ('radio', 'checkbox'):
                    if field_element.get('value') in field_values[field_name]:
                        field_element['checked'] = ''
                    else:
                        del field_element['checked']
                else:
                    field_element['value'] = field_values[field_name][0]
            elif field_element.name == 'select':
                for option_element in field_element.find_all('option'):
                    option_element = cast(Tag, option_element)
                    if option_element.get('value') in field_values[field_name]:
                        option_element['selected'] = ''
                    else:
                        del option_element['selected']
            elif field_element.name == 'textarea':
                string_content = NavigableString(field_values[field_name][0])
                field_element.contents = [string_content]

    def _populate_data(self, form_element: Tag, data_values: Dict[str, str]) -> None:
        """
        Inserts the provided values as `data` attributes in the exercise
        element.
        """
        for data_key, data_value in data_values.items():
            full_data_key = f'data-{data_key}'
            form_element[full_data_key] = data_value

    def _remove_submit_button(self, form_element: Tag) -> None:
        """
        Removes all submit buttons from the exercise element.
        """
        for submit_element in form_element.find_all(['input', 'button'], type='submit'):
            cast(Tag, submit_element).decompose()
