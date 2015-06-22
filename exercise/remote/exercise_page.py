from bs4 import BeautifulSoup


class ExercisePage:
    """
    This class is used for representing the pages that are received from exercise
    services as objects. The pages have both submission related fields, such as
    'is_graded' and 'points', as well as meta information such as 'title' and
    'description'.
    """
    def __init__(self, exercise, response_body=None):
        """
        Create a new exercise page for the given exercise. If a page is already
        requested, its HTML content may be given as a parameter, and the fields
        of the ExercisePage will be filled with data that is parsed from the
        page.
        
        @param exercise: an exercise object, which must inherit BaseExercise
        @param response_body: an optional HTML string containing either an exercise
                         description or feedback page
        """
        self.response = response_body
        self.exercise = exercise
        self.is_graded = False
        self.is_accepted = False
        self.points = 0
        self.max_points = exercise.max_points
        self.content = ""
        self.instructions = exercise.instructions
        self.meta = {
            "title": exercise.name,
            "description": exercise.description
        }
        self.errors = []

        if response_body != None:
            self._parse_response()

    def _parse_response(self):
        
        soup = BeautifulSoup(self.response)
        head = soup.find("head")

        max_points = self._get_value_from_soup(
            head, "meta", "value", {"name": "max-points"})
        if max_points != None:
            self.max_points = int(max_points)

        if self._get_value_from_soup(
            head, "meta", "value", {"name": "status"}) == "accepted":
            self.is_accepted = True

        meta_title = self._get_value_from_soup(
            head, "meta", "content", {"name": "DC.Title"})
        if meta_title:
            self.meta["title"] = meta_title
        else:
            title = soup.find("title")
            if title:
                self.meta["title"] = title.contents

        description = self._get_value_from_soup(
            head, "meta", "content", {"name": "DC.Description"})
        if description:
            self.meta["description"] = description

        points = self._get_value_from_soup(head, "meta", "value", {"name": "points"})
        if points != None:
            self.points = int(points)
            self.is_graded = True
            self.is_accepted = True

        exercise_div = soup.body.find("div", {"id": "exercise"})
        if exercise_div != None:
            self.content = exercise_div.renderContents()
        else:
            self.content = soup.body.renderContents()
    
    def is_sane(self):
        """
        Checks that the parsed values are sane/acceptable.
        
        """
        return self.points <= self.max_points \
            and not (self.exercise.max_points != 0 \
                     and self.max_points == 0)

    def _get_value_from_soup(self, soup, tag_name, attribute, parameters={}, default=None):
        """
        This is a helper function for finding a specific attribute of an element from
        a HTML soup. The element may be searched with a tag name and parameters. If the
        element or attribute is not found, the 'default' or None value will be returned.
    
        @param soup: a BeautifulSoup object
        @param tag_name: the name of an HTML tag as a string, for example "div"
        @param attribute: the attribute to read from the tag
        @param parameters: an optional dictionary of keys and values which the element must match
        @param default: a value, which will be returned if no matching element or attribute is found
    
        @return: the value of the requested attribute from the HTML element. If matching value is not found
        the given default or None is returned
        """
        element = soup.find(tag_name, parameters)
        if element != None:
            return element.get(attribute, default)
        return default
