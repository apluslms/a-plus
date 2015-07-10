A+ course module content
========================

A+ can present study content as modules or chapters of a course.
Similarly to the exercises the content is integrated from external
sources.

## External HTML

"Teacher" configures the `content_url` for the course module. The HTML
may include following elements to inject A+ functionality in the page.

### Exercise

    <div
      data-exercise-url="http://aplus.domain.org/course/2015/exercises/1/"
      data-exercise-quiz />

Embeds a fully functioning exercise to the content including student
submission status.

* `data-exercise-url`

  An URL address to an A+ exercise. There are no checks for the exercise
  to belong to the same content module but this is strongly advised to
  keep points and opening times coherent.

* `data-exercise-quiz`

  If attribute is present the exercise feedback will take the place of
  the exercise instruction. This works for quiz type exercises where
  the feedback includes the student answer and chance to post changes.
