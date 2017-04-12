
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
