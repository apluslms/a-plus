A+ course chapter content
=========================

A+ can present course chapters that integrate page content from external
source. The chapters can embed A+ learning objects from the course module.

## External HTML

"Teacher" creates chapter objects in the A+ and configures
the `content_url` for them. On chapter view the URL is requested and
the response BODY (or if `<div id="chapter">` exists) will be presented
to the student. The HTML may include following elements to inject A+
functionality in the page.

### Exercise

    <div
      data-exercise-url="http://aplus.domain.org/course/2015/exercises/1/"
      data-exercise-quiz></div>

Embeds a fully functioning exercise to the content including student
submission status.

* `data-exercise-url`

  An URL address to an A+ exercise. There are no checks for the exercise
  to belong to the same course module but this is strongly advised to
  keep point sums and schedule times coherent.

* `data-exercise-quiz`

  If attribute is present the exercise feedback will take the place of
  the exercise instruction. This works for quiz type exercises where
  the feedback includes the student answer and chance to post changes.
