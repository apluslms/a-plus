from django.db import models
from django.utils.text import format_lazy
from django.utils.translation import gettext_lazy as _

from course.models import (
    CourseInstance,
    CourseModule,
    LearningObjectCategory,
)
from exercise.cache.hierarchy import NoSuchContent
from exercise.models import BaseExercise


class Threshold(models.Model):
    """
    Course may set thresholds that signify module access or course grades.
    """
    course_instance = models.ForeignKey(CourseInstance, on_delete=models.CASCADE,
        related_name="thresholds")
    name = models.CharField(max_length=255)
    passed_modules = models.ManyToManyField(CourseModule, blank=True)
    passed_categories = models.ManyToManyField(LearningObjectCategory, blank=True)
    passed_exercises = models.ManyToManyField(BaseExercise, blank=True)
    consume_harder_points = models.BooleanField(default=False,
        help_text=_('HARDER_POINTS_CONSUMED_BY_EASIER_DIFFICULTY_REQUIREMENTS'))

    def __str__(self):
        return self.name + " " + self.checks_str()

    def checks_str(self):
        checks = [
            " ".join(str(m) for m in self.passed_modules.all()),
            " ".join(str(c) for c in self.passed_categories.all()),
            " ".join(str(e) for e in self.passed_exercises.all()),
            " ".join(str(p) for p in self.points.all()),
        ]
        return " ".join(checks)

    def is_passed(self, cached_points, unconfirmed=False):
        try:
            for module in self.passed_modules.all():
                entry,_,_,_ = cached_points.find(module)
                if not entry["passed"]:
                    return False
            for category in self.passed_categories.all():
                if not cached_points.find_category(category.id)["passed"]:
                    return False
            for exercise in self.passed_exercises.all():
                entry,_,_,_ = cached_points.find(exercise)
                if not entry["passed"]:
                    return False
        except NoSuchContent:
            return False

        total = cached_points.total()
        d_points = total["points_by_difficulty"].copy()
        if unconfirmed:
            u_points = total["unconfirmed_points_by_difficulty"]
            for key,value in u_points.items():
                if key in d_points:
                    d_points[key] += value
                else:
                    d_points[key] = value
        return self._are_points_passed(total["points"], d_points)

    def _are_points_passed(self, points, points_by_difficulty):
        if self.points.count() == 0:
            return True
        d_points = points_by_difficulty.copy()
        ds,ls = zip(*list((p.difficulty,p.limit) for p in self.points.all()))
        for i,d in enumerate(ds):
            if d:

                if self.consume_harder_points:
                    p = d_points.get(d, 0)
                    l = ls[i]
                    if p < l:
                        for j in range(i + 1, len(ds)):
                            jd = ds[j]
                            jp = d_points.get(jd, 0)
                            if jp > l - p:
                                d_points[jd] -= l - p
                                d_points[d] = l
                                break
                            else:
                                p += jp
                                d_points[d] = p
                                d_points[jd] = 0
                    else:
                        continue

                if d_points.get(d, 0) < ls[i]:
                    return False

            elif points < ls[i]:
                return False

        return True


class ThresholdPoints(models.Model):
    threshold = models.ForeignKey(Threshold, on_delete=models.CASCADE,
        related_name="points")
    limit = models.PositiveIntegerField()
    difficulty = models.CharField(max_length=32, blank=True)
    order = models.PositiveIntegerField(default=1)

    class Meta:
        ordering = ['threshold', 'order']

    def __str__(self):
        if self.difficulty:
            return "{} {:d}".format(self.difficulty, self.limit)
        return format_lazy(
            _('POINTS -- {:d}'),
            self.limit
        )


class CourseModuleRequirement(models.Model):
    module = models.ForeignKey(CourseModule, on_delete=models.CASCADE,
        related_name="requirements")
    threshold = models.ForeignKey(Threshold, on_delete=models.CASCADE)
    negative = models.BooleanField(default=False)

    def __str__(self):
        if self.negative:
            return "< " + self.threshold.checks_str()
        return self.threshold.checks_str()

    def is_passed(self, cached_points):
        passed = self.threshold.is_passed(cached_points, True)
        return not passed if self.negative else passed


# TODO: should implement course grades using thresholds
# TODO: should refactor diploma to use course grades
