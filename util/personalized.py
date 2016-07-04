'''
Utility functions for handling personalized exercise content.

Personalized content is stored in mooc-grader/exercises-meta directory
(by default, see settings.PERSONALIZED_CONTENT_PATH).

mooc-grader/exercises-meta/<course_key>/pregenerated/<exercise_key>/ is created
when the personalized exercises are generated and holds the different instances
of the exercise.

mooc-grader/exercises-meta/<course_key>/users/<user_ids>/<exercise_key>/ has
directory "personal" in which personal files can be stored after grading and
a link "generated" that points to the exercise instance assigned to the user is
created at the start of grading (prepare action). (The generated link is always
created in the prepare action because the exercise instance may change after
the user has submitted too many times, if the exercise has enabled regeneration.)
'''
from django.conf import settings
from django.core.urlresolvers import reverse
import os
import shutil
import logging
import random
import access.config
from access.types.auth import get_uid, user_ids_from_string
from .shell import invoke

LOGGER = logging.getLogger('main')

class ExerciseGenerationError(Exception):
    pass


def user_personal_directory_path(course, exercise, userid):
    '''
    Return path to the personal directory of the user that has link "generated"
    to the assigned exercise instance and directory "personal".
    '''
    return os.path.join(settings.PERSONALIZED_CONTENT_PATH,
        course["key"], "users", userid, exercise["key"])


def pregenerated_exercises_directory_path(course, exercise):
    '''
    Return path to the directory of pregenerated exercise instances
    (instances are directories under this directory).
    '''
    return os.path.join(settings.PERSONALIZED_CONTENT_PATH,
        course["key"], "pregenerated", exercise["key"])


def prepare_user_personal_directory(course, exercise, userid):
    '''
    Create the personal directory of the user (unless the directory already exists).
    '''
    user_dir = user_personal_directory_path(course, exercise, userid)
    personal_dir = os.path.join(user_dir, 'personal')
    # Create empty directory unless it already exists
    if not os.path.exists(personal_dir):
        try:
            os.makedirs(personal_dir)
        except OSError:
            pass # someone else created the dir after executing the if condition


def prepare_pregenerated_exercises_directory(course, exercise):
    '''
    Create the base directory for pregenerated exercise instances.
    '''
    pregen_dir = pregenerated_exercises_directory_path(course, exercise)
    # Create empty directory unless it already exists
    try:
        os.makedirs(pregen_dir)
    except OSError:
        return # it exists


def pregenerated_exercise_instances(course, exercise):
    '''
    Return a list of the existing pregenerated exercises instances (directory names).
    '''
    pregenerated_dir = pregenerated_exercises_directory_path(course, exercise)
    try:
        # return a list of directory names (not full paths)
        return [instance_dir for instance_dir in os.listdir(pregenerated_dir) 
                if os.path.isdir(os.path.join(pregenerated_dir, instance_dir))]
    except OSError:
        return [] # pregenerated_dir does not exist


def select_generated_exercise_instance(course, exercise, userids_str, submission_number):
    '''
    Return path to the generated exercise instance that is assigned to the user(s).
    The instance may change as more submissions are made if the exercise has
    enabled regeneration.
    '''
    pregenerated_dir = pregenerated_exercises_directory_path(course, exercise)
    userids = sum(user_ids_from_string(userids_str))
    instances = pregenerated_exercise_instances(course, exercise)
    num_instances = len(instances)
    if num_instances == 0:
        raise access.config.ConfigError("Exercise is personalized but no exercise instances have been pregenerated")
    
    if "max_submissions_before_regeneration" in exercise:
        # the generated exercise may be regenerated after submitting certain amount of times
        instance_numbers = list(range(num_instances))
        # use numbers in the list so that the directory listing order (in instances) does not cause surprises
        r = random.Random(userids)
        r.shuffle(instance_numbers)
        instance = instance_numbers[((submission_number - 1) // exercise["max_submissions_before_regeneration"]) % num_instances]
    else:
        # the generated exercise of the user does not change as more submissions are made
        instance = userids % num_instances

    return os.path.join(pregenerated_dir, str(instance))


def read_user_personal_file(course, exercise, userid, filename, generated=False, submission_number=1):
    '''
    Return the contents of a personal file of the user(s).
    '''
    user_dir = user_personal_directory_path(course, exercise, userid)
    if generated:
        # file from the generated exercise instance, the instance depends on
        # the user and submission number
        filepath = os.path.join(
                        select_generated_exercise_instance(course, exercise, userid, submission_number),
                        filename)
    else:
        # personal file stored for the user
        filepath = os.path.join(user_dir, 'personal', filename)
    try:
        with open(filepath) as f:
            return f.read()
    except IOError:
        return ''


def read_generated_exercise_file(course, exercise, instance, filename):
    '''
    Return the contents of a file from a generated exercise instance.
    '''
    generated_dir = pregenerated_exercises_directory_path(course, exercise)
    try:
        with open(os.path.join(generated_dir, instance, filename)) as f:
            return f.read()
    except IOError:
        return ''


def delete_pregenerated_exercise_instances(course, exercise):
    '''
    Delete pregenerated exercise instances (directories).
    '''
    pregen_dir = pregenerated_exercises_directory_path(course, exercise)
    try:
        for entry in os.listdir(pregen_dir):
            # only delete directories under the parent directory
            file_path = os.path.join(pregen_dir, entry)
            if os.path.isdir(file_path):
                shutil.rmtree(file_path)
    except OSError:
        pass # the directory may not exist yet


def generate_exercise_instances(course, exercise, number_of_instances):
    '''
    Generate the given number of new exercise instances.
    '''
    existing_instances = pregenerated_exercise_instances(course, exercise)
    # instance directories are named with integers, find the next unused integer
    index = -1
    for inst in existing_instances:
        try:
            inst = int(inst)
            if inst > index:
                index = inst
        except ValueError:
            pass
    index += 1
    
    pregen_dir = pregenerated_exercises_directory_path(course, exercise)
    # this base directory should already exist
    for _ in range(number_of_instances):
        instance_path = os.path.join(pregen_dir, str(index))
        os.mkdir(instance_path)
        result = generate_one_exercise_instance(course, exercise, instance_path)
        if result["code"] != 0:
            LOGGER.debug("Exercise generator failed: exit status %s", result["code"])
            LOGGER.debug("Exercise generator stdout: %s", result["out"])
            LOGGER.debug("Exercise generator stderr: %s", result["err"])
            raise ExerciseGenerationError("Exercise generator failed: exit status %s\nStderr: %s" % (result["code"], result["err"]))
        index += 1


def generate_one_exercise_instance(course, exercise, dir_path):
    '''
    Generate one new exercise instance in the given directory.
    '''
    if not ("generator" in exercise and "cmd" in exercise["generator"]):
        raise access.config.ConfigError(
                'Missing "generator" and/or "cmd" under "generator" in the exercise configuration %s/%s' %
                (course["key"], exercise["key"]))
    
    cwd = None
    if "cwd" in exercise["generator"]:
        # cwd path in the exercise config should start from the course directory
        cwd = os.path.join(access.config.DIR, exercise["generator"]["cwd"])
    
    command = exercise["generator"]["cmd"][:] # copy the command list from config before appending
    command.append(dir_path)
    return invoke(command, cwd)


def personalized_template_context(course, exercise, request):
    '''
    Return template context for the given personalized exercise and user(s).
    Prepares the user personal directory if it does not yet exist.
    '''
    ctx = {}
    if not ("personalized" in exercise and exercise["personalized"]):
        return ctx
    
    userid = get_uid(request)
    if not userid:
        raise access.config.ConfigError('Exercise is personalized but HTTP GET request did not supply any "uid" parameter.')
    # create the personal directory
    prepare_user_personal_directory(course, exercise, userid)
    
    if "generated_files" not in exercise:
        raise access.config.ConfigError('"generated_files" missing in the configuration of a personalized exercise')
    
    # prepare template context (variables about the pregenerated exercise instance files)
    generated_files = {}
    for gen_file_conf in exercise["generated_files"]:
        if "file" not in gen_file_conf:
            raise access.config.ConfigError('"file" under "generated_files" missing in the exercise configuration')
        file_ctx = {}
        file_ctx["file"] = gen_file_conf["file"]
        submission_number = int(request.GET.get("ordinal_number", 1))
        if "url_in_template" in gen_file_conf and gen_file_conf["url_in_template"]:
            exercise_instance = os.path.basename(select_generated_exercise_instance(
                    course, exercise, userid, submission_number))
            # URL to download the exercise generated file
            file_ctx["url"] = reverse('generated-file',
                    args=(course["key"], exercise["key"], exercise_instance, gen_file_conf["file"]))
        if "content_in_template" in gen_file_conf and gen_file_conf["content_in_template"]:
            # read contents of the exercise generated file to a variable
            file_ctx["content"] = read_user_personal_file(course, exercise,
                    userid, gen_file_conf["file"], True, submission_number)
        generated_files[gen_file_conf["key"]] = file_ctx
    
    ctx["generated_files"] = generated_files
    return ctx
