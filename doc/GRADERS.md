A+ grader service protocols
===========================

The philosophy of A+ is to integrate external grader services into the course environment.
The graders should be stateless and need only to worry about grading a submission.

## Authentication and Authorization

Every incoming and outgoing request must either have a A+-provided grading
token as a GET parameter (included in the `submission_url` below) or a JWT
authentication token attached in the Authorization header:

    Authorization: bearer <token>

For more information on the JWT token, see [AUTH](AUTH.md).

## BaseExercise (A+ HTTP protocol)

Easy programming of a custom grader is a priority. The protocol does not limit the
parties initiating grading. The grader privacy should be secured by keeping
grader services in private network.
"Teacher" configures the `service_url` for the exercise.

### Upon student viewing the exercise, A+ issues a request:

`HTTP GET service_url` with additional **GET parameters**:

* `submission_url`

	Unique address for asynchronously *creating a new graded submission*.

* `post_url`

	Unique address for posting a submission form.

* `max_points`

	The maximum points for this exercise set by "teacher" in A+.

* `uid`

	User identifier(s) of the student(s) who is/are viewing the exercise.
	UIDs are not the same as student ids.
	If there is more than one student, the UIDs (integers) are sorted and combined
	into one string with dash as the separator, e.g., "2-14-458".

* `ordinal_number`

	Ordinal number of the next submission that the student has not yet made, i.e.,
	the value is incremented by one from the current count of submissions.
	The first submission has ordinal number one. If the exercise changes as
	the submission count increases, the state of the exercise when viewing it
	matches the state when a new submission is made and graded.

The grader service responds with an HTML document. The BODY (or if `<div id="exercise">`
exists) will be presented to the student. Normally the content will include a FORM
posting a submission with any exercise values or files.
The FORM must use empty (or `post_url`) as ACTION.

### Upon receiving a student submission FORM POST, A+ issues a request:

`HTTP POST service_url` with **user POST parameters** and additional **GET parameters**:

* `submission_url`

	Unique address for asynchronously *grading this submission*.

* `post_url`

	Unique address for posting a new submission form.

* `max_points`

	The maximum points for this exercise set by "teacher" in A+.

* `uid`

	Same as when viewing the exercise. User identifier(s) of the student(s)
	submitting to the exercise.

* `ordinal_number`

	Ordinal number of the new submission that is going to be graded.
	The first submission has ordinal number one.

The grader service responds with an HTML document. The BODY (or if `<div id="exercise">`
exists) will be presented to the student. Normally the content includes feedback
for the received submission. If a FORM is offered for refining the
submission it must use the `post_url` as ACTION. Additionally the following
`<META name="name" value="value" />` elements are used in the **response HEAD**:

* `status` (required)

	`"accepted"`: The submission is accepted for grading.

	`"rejected"`: The submission is invalid for grading.

	`"error"`: Failed to grade the submission.

* `points` (optional)

	Sets the grade for the submission and finishes the grading. If manually
	grading or asynchronously grading from a queue the points must not
	be set.

* `max_points` (recommended)

	Grades on a different scale than set in A+. If set the final A+ points
	will be scaled to match the maximum points set by "teacher" in A+.

* `wait` (optional)

	Suggests waiting for the asynchronous grading finishing in a short time.

* `DC.Title` (optional)

	A title for the exercise. May be overridden by the "teacher" in A+.

* `DC.Description` (optional)

	A description of the exercise. May be overridden by the "teacher" in A+.

### Upon asynchronously grading, GRADER issues a request:

`HTTP POST submission_url` with **POST parameters**:

* `points` (required)

* `max_points` (required)

* `feedback` (optional)

	Feedback presented to the student for the submission.

* `grading_payload` (optional)

	Payload stored in the submission for course staff. If the submission
	was not created with FORM POST this is important for later investigations.

* `error` (optional)

	Sets the submission to an error state.

The request must come from an IP address that is resolved from the `service_url`
set by "teacher" in the A+. A GET request to the `submission_url` is responded
with JSON describing the current user and exercise status.


## ExerciseWithAttachment

A variation of the *BaseExercise* where "teacher" in A+ writes exercise instruction,
lists the file names for student to submit and loads an exercise attachment file
for the grader.

### Upon student viewing the exercise, A+ creates the submission form.

The grader service is not requested at this point.

### Upon receiving a student submission FORM POST, A+ issues a request:

`HTTP POST service_url` as in *BaseExercise* with **POST parameters**:

* `content_0`

	The trusted exercise attachment file.

* `file_N`

	Submission file name N=1,2,3,...

* `content_N`

	Student submission file N=1,2,3,...
