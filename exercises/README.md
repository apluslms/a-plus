Course and exercise configuration
=================================

## Configuration files

Configuration is written as JSON or YAML in exercises-directory. Each subdirectory
holding an `index.json` or `index.yaml` is a valid active course. It is recommended
that each course is checkout as a submodule in the exercises-directory.

	git submodule add (repository) exercises/(course_key)

The submodules will not be stored in the mooc-grader repository.

1. ### course_key/index.[json|yaml]
	* The directory name acts as a course key, which is used in
		* URLs: `/course_key`
	* `name`: A public complete course name
	* `contact`: A private contact email for course configuration
	* `description` (optional): A private course description
	* `lang` (optional): A course language code to insert in HTML and
		to select alternative templates named `template.html.lang`.
		Default templates support finnish "fi" and fallback to english.
	* `exercises`: a list of active exercise keys

2. ### course_key/exercise_key.[json|yaml]
	* The file name acts as an exercise key, which is used in
		* URLs: `/course_key/exercise_key`
		* Must match the exercise list in `index.[json|yaml]`
	* `title`: A title of the exercise
	* `description` (optional): An exercise description (Dublin Core metadata)
	* `instructions` (optional): Most default templates will print given
		instructions HTML before the exercise widgets.
	* `max_points` (optional): The maximum exercise points (positive int).
		Overrides any maximum points reported by test actions.
	* `view_type`: A dotted name for an exercise implementation
	Rest of the attributes are exercise type specific.

3. ### course_key/sandbox
	* A directory for sandbox environment content. Directory is copied into
	sandbox as `/usr/local/sandbox/course_key`. Any files beginning with
	`install-` will be run inside the sandbox in alphabetical order during
	the `manage_sandbox.sh` run. Many common requirements can be filled by
	copying install scripts from `scripts/sandbox_available`.

## Exercise view types

Common exercise views are implemented in `access.types` and they should fit most
purposes by configuration and templating. However, it is possible to implement a
course specific exercise view in a course specific Python module.

1. ### access.types.stdasync.acceptFiles
	Accepts named files for asynchronous grading queue. Extended attributes:
	* `files`: list of expected files
		* `field`: file field name
		* `name`: actual file name, may include subdirectories
	* `template` (default `access/accept_files_default.html`):
		name of a template to present
	* `feedback_template` (default `access/task_success.html`):
		name of a template used to format the feedback
	* `actions`: list of asynchronous test actions

2. ### access.types.stdasync.acceptAttachedExercise
	Accepts attached exercise rules and user files for asynchronous
	grading queue. Extended attributes:
	* `template` (default `access/accept_files_default.html`):
		name of a template to present.
		This test is used with exercises configured externally
		where also the creation of the form should be taken care off.
		Post should include several file fields named `file[]` where
		the first file is an exercise rule attachment and rest are
		user files which are named by `file_N` post fields in order.
		(Format is used by A+ exercises with attachments).
	* `feedback_template` (default `access/task_success.html`):
		name of a template used to format the feedback
	* `actions`: list of asynchronous test actions

3. ### access.types.stdasync.acceptGitAddress
	Writes the Git address into user/gitsource file for asynchronous grading
	queue. See grader.actions.git*. Extended attributes:
	* `require_gitlab` (optional):
		a host name for a gitlab installation.
		Makes sure that the address is an SSH repo path or any HTTP URL
		in given Gitlab host. Stores the standard SSH path for key access.
	* `template` (default: `access/accept_git_default.html`):
		name of a template to present
	* `feedback_template` (default `access/task_success.html`):
		name of a template used to format the feedback
	* `actions`: list of asynchronous test actions

4. ### access.types.stdsync.createForm
	Synchronous form checker. Requires `max_points` in the
	exercise configuration. If form has no points configured then maximum
	points are granted on errorless submission. Extended attributes:
	* `fieldgroups`: list of field groups
		* `name` (optional): group name (fieldset legend)
		* `fields`: list of fields
			* `title` (optional): field title or label
			* `more` (optional): more instructions
			* `include` (optional): template name to include
				as content in more instructions
			* `type`: `radio`/`checkbox`/`text`/`textarea`
			* `points` (optional): number of points to grant
			* `required` (optional): `true` to require an answer
			* `correct` (optional): exact correct answer for text fields
			* `regex` (optional): regex to match correct answer for text fields
			* `options` list of options for choice fields
				* `label`: option label
				* `correct` (optional): `true` for correct option.
					Checkbox requires all and only correct
					options selected. Radio requires one of
					the correct options selected. If no correct
					options are configured anything is correct.
	* `template` (default `access/create_form_default.html`): name of a template to present

5. ### access.types.stdsync.comparePostValues
	Synchronous check against posted values. Requires `max_points` in the
	exercise configuration. If values have no points configured then maximum
	points are granted on errorless submission. Extended attributes:
	* `values`: map of POST field names to rules:
		* `accept`: list of accepted values, [ False ] for no value, [ True ]
			for any value
		* `points` (optional): number of points to grant or negative to deduct
	* `template`: name of a template to present. Template should manually
		include a form that produces the expected POST values.

6. ### access.types.stdsync.noGrading
	Presents a template and does not grade anything. Extended attributes:
	* `template`: name of a template to present

## Test action types

Asynchronous exercises configure a list of `actions`. Actions will run in
listed order.

* ### Common attributes for each action
	* `type`: A dotted name for a test action implementation
	* `points` (optional): Overrides any points reported
		by the action. Passed action awards all points.
		Failed action awards zero points.
	* `title` (optional): grading action title in template
	* `html` (optional): true to pass output as HTML in template
	Rest of the attributes are action type specific

### Action types

Common test actions are implemented in `grader.actions` and they should
fit most purposes by configuration. However, it is possible to implement a
course specific test actions in a course_key.actions Python module. Typically
the actual tests should be written as programs or scripts run inside the safe
sandbox system.

1. ### grader.actions.prepare
	Does preparations on the submitted files. Additional attributes:
	* `charset`: a character set where to convert submitted files to
	* `add`: a directory including files to add to the user submission
		e.g. `course_key/exercise_name` for support and test code
	* `unzip`: a received file name to unzip
	* `pull`: a file to pull outside from the user directory
		e.g. `exercise_attachment` for later comparison

2. ### grader.actions.sandbox
	Executes a command inside the chroot sandbox as a restricted user.
	Picks points from `TotalPoints: N` and/or `MaxPoints: N` lines if
	printed out. Additional attributes:
	* `cmd`: command line as an ARRAY
	* `net` (optional): `true` to use network enabled sandbox user
	* `time` (optional): limit the seconds the command can run
	* `memory` (optional): limit the memory bytes (address space) the command
		can take, use 10k for kilobytes and 10m for megabytes
	* `files` (optional): limit the number of file descriptors the command can
		open
	* `disk` (optional): limit the disk bytes the command can write, use 10k
		for kilobytes and 10m for megabytes

3. ### grader.actions.sandbox_python_test
	Executes a command that should run a Python unittest inside the chroot
	sandbox as a restricted user. This is identical to the normal sandbox
	action except that the stderr (unittest output) is presented as stdout and
	the real stdout is nulled. Note that at the end of the complete test run
	(e.g. def tearDownClass) the `TotalPoints: N` and `MaxPoints: N` lines
	should be printed out.

4. ### grader.actions.gitlabquery
	Requires the acceptGitAddress view type with require_gitlab set.
	Queries the Gitlab API and checks desired properties. Additional attributes:
	* `token`: a Gitlab account private token for API access
	* `private` (optional): True, stop if public access
	* `forks` (optional): Project ID, stop if not forked from this

5. ### grader.actions.gitclone
	Works with the acceptGitAddress view type. Tries to clone the
	repository. Additional attributes:
	* `files` (optional): a space separated list of files to select for
		submission from the repository. The files are moved into the
		normal user submission directory and contents are listed in the
		feedback.
	* `read` (optional): override the file where the git address is read from

6. ### grader.actions.expaca
	Executes the expaca testing application. The expaca is not freely available
	and this action requires the expaca properly installed. Additional
	attributes:
	* `attachment` (alternative): True, if acceptAttachedExercise is used
	* `testdir` (alternative): a directory including expaca test
		e.g. course_key/exercise_name
	* `rulefile` (optional): inside test, default `checkingRule.xml`
	* `modeldir` (optional): inside test, default `model`
	* `filesdir` (optional): inside test, default `CheckingFiles`
	* `xslt_transform` (optional): a name of an XSL style file for
		transforming expaca XML output

## Default sandbox scripts

Following common scripts are provided by default and copied into
/usr/local/sandbox inside sandbox. They may be used in the
sandbox command line.

* java_compile.sh
	Compiles all java files in submission. Args:
	* `--cp` (optional): classpath to use
	* `--clean` (optional): `yes` to remove java source after compilation

* scala_compile.sh
	Compiles all scala files in submission. Args:
	* `--cp` (optional): classpath to use
	* `--clean` (optional): `yes` to remove scala source after compilation

* python_run.sh
	Passes a call to python interpreter. Implements extra arg:
	* `--virtualenv` (optional): activates named virtualenv for the command

* template.sh
	An example of a grading shell script. Will list submission files and
	always grade 10/10 points.

## Templates

Many type views can use a named template. The templates can be placed in
exercise directory and use subdirectories. The available variables are
listed below.

1. ### All templates
	* `course`: course configuration dictionary
	* `exercise`: exercise configuration dictionary

	Note that you can add any new keys to configuration and utilize them in templates.

2. ### Templates for asynchronous submissions
	* `result`: object holding POST results or None
		* `error`: True on failed POST
		* `missing_url`: True if no submission_url provided
		* `missing_files`: True if files missing
		* `missing_file_name`: True if file name missing
		* `invalid_address`: True if Gitlab address is rejected
		* `accepted`: True if accepted for grading
		* `wait`: True if the grading should be finished in a moment
	A default file submission form can be included with

		{% include 'access/accept_files_form.html' %}

3. ### Feedback templates for asynchronous submissions
	* `result`: object holding test results
		* `points`: total points granted
		* `max_points`: total maximum points
		* `tests`: entry for each test action
			* `points`: points granted
			* `max_points`: maximum points
			* `out`: test output
			* `err`: test errors
			* `stop`: True when rest of the actions
				were cancelled

4. ### Templates for createForm
	* `result`: object holding form and results
		* `form`: a Django form object
		* `accepted`: True if valid form POST was graded
		* `points`: granted points
		* `error_groups`: list of group_N names having errors
		* `error_fields`: list of field_N names having errors
	A default form can be included with

		{% include 'access/graded_form.html' %}

5. ### Templates for comparePostValues
	* `result`: object holding POST results or None
		* `accepted`: True
		* `received`: map of received POST fields => values
		* `points`: granted points
		* `failed`: list of failed field names
