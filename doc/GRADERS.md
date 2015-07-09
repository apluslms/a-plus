A+ grader service protocols
===========================

The philosophy of A+ is to integrate external grader services into the course environment.
The graders should be stateless and need only to worry about grading a submission.


## BaseExercise (A+ HTTP protocol)

"Teacher" configures the service URL for the exercise.

### Upon student viewing the exercise, A+ issues a request:

	HTTP GET service_url WITH additional GET parameters:
	
	* submission_url
		Unique address for asynchronously *creating a new graded submission*.
	* post_url
		Unique address for posting a submission form.
	* max_points
		The maximum points for this exercise set by "teacher" in A+.

The grader service responds with an HTML document. The BODY (or if a DIV element
with ID="exercise" exists) will be presented to the student. Normally the
content will include a FORM posting a submission with any exercise values or files.
The FORM must use empty (or *post_url*) as ACTION.

### Upon receiving a student submission FORM POST, A+ issues a request:

	HTTP POST service_url WITH user POST parameters and additional GET parameters:
	
	* submission_url
		Unique address for asynchronously *grading this submission*.
	* post_url
		Unique address for posting a new submission form.
	* max_points
		The maximum points for this exercise set by "teacher" in A+.

The grader service responds with an HTML document. The BODY (or if a DIV element
with ID="exercise" exists) will be presented to the student. The content includes
feedback for the received submission. If a FORM is offered for refining the
submission it must use the *post_url* as ACTION. Additionally the following
`<META name="name" value="value" />` elements are used in the response HEAD:

	* status (required)
		"accepted": The submission is accepted for grading.
		"error": The submission can not be graded.
	* points (optional)
		Sets the grade for the submission and finishes the grading. If manually
		grading or asynchronously grading from a queue the points must not
		be set.
	* max_points (recommended)
		Grades on a different scale than set in A+. If set the final A+ points
		will be scaled to match the maximum points set by "teacher" in A+.
	* wait (optional)
		Suggests waiting for the asynchronous grading finishing in a short time.
	* DC.Title (optional)
		A title for the exercise. May be overridden by the "teacher" in A+.
	* DC.Description (optional)
		A description of the exercise. May be overridden by the "teacher" in A+.

### Upon asynchronously grading a submission, grader issues a request:

	HTTP POST submission_url WITH POST parameters:
	
	* points (required)
	* max_points (required)
	* feedback (optional)
		Feedback presented to the student for the submission.
	* grading_payload (optional)
		Payload stored in the submission for course staff. If the submission
		was not created with FORM POST this is important for later investigations.
	* error (optional)
		Sets the submission to an error state.

The request must come from an IP address that is resolved from the *service_url*
set by "teacher" in the A+. A GET request to the *submission_url* is responded
with JSON describing the user and exercise status.


## ExerciseWithAttachment

A variation of the *BaseExercise* where "teacher" in A+ writes exercise instruction,
lists the file names for student to submit and loads an exercise attachment file
for the grader.

### Upon student viewing the exercise, A+ creates the submission form.

### Upon receiving a student submission FORM POST, A+ issues a request:

	HTTP POST service_url AS in BaseExercise WITH POST parameters:
	
	* content_0: the trusted exercise attachment file
	* file_N: submission file name 1...N
	* content_N: student submission file 1...N
