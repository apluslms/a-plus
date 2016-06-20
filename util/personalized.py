'''
Utility functions for handling personalized exercise content.

Personalized content is stored in mooc-grader/exercises-meta directory
(by default, see settings.PERSONALIZED_CONTENT_PATH).

mooc-grader/exercises-meta/<course_key>/pregenerated/<exercise_key>/ is created
when the personalized exercises are generated and holds the different instances
of the exercise.

mooc-grader/exercises-meta/<course_key>/users/<user_ids>/<exercise_key>/ has
a link "generated" that points to the exercise instance assigned to the user and
directory "personal" in which personal files can be stored after grading.
'''
from django.conf import settings
import os
import random
import shutil
import logging
import access.config
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
    Create the personal directory of the user and assign an exercise instance
    to the user (unless the directory already exists).
    '''
    user_dir = user_personal_directory_path(course, exercise, userid)
    personal_dir = os.path.join(user_dir, 'personal')
    # Create empty directory unless it already exists
    if not os.path.exists(personal_dir):
        try:
            os.makedirs(personal_dir)
        except OSError:
            return # someone else created the dir after executing the if condition

    try:
        # link the user to a randomly selected generated exercise instance
        generated_dir = select_random_exercise_instance(course, exercise)
        os.symlink(generated_dir, os.path.join(user_dir, 'generated'))
    except OSError:
        pass # the generated link already exists
    
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
    
def select_random_exercise_instance(course, exercise):
    '''
    Return the full path to a randomly selected generated exercise instance directory.
    '''
    pregenerated_dir = pregenerated_exercises_directory_path(course, exercise)
    instances = pregenerated_exercise_instances(course, exercise)
    if not instances: # empty
        raise access.config.ConfigError("Exercise is personalized but no exercise instances have been pregenerated")
    return os.path.join(pregenerated_dir, random.choice(instances))

def read_user_personal_file(course, exercise, userid, filename, generated=True):
    '''
    Return the contents of a personal file of the user(s).
    '''
    user_dir = user_personal_directory_path(course, exercise, userid)
    if generated:
        filepath = os.path.join(user_dir, 'generated', filename)
    else:
        filepath = os.path.join(user_dir, 'personal', filename)
    try:
        with open(filepath) as f:
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

def regenerate_user_exercise(course, exercise, userid):
    '''
    Change the generated exercise instance assigned to the user to another instance.
    '''
    user_dir = user_personal_directory_path(course, exercise, userid)
    try:
        generated_link = os.path.join(user_dir, 'generated')
        old_instance = os.path.basename(os.readlink(generated_link))
        # remove the old link
        os.unlink(generated_link)
    except OSError:
        # the link did not exist, create it as new
        prepare_user_personal_directory(course, exercise, userid)
        return
    
    # select a new, different generated exercise instance
    generated_dir = old_instance
    
    instances = pregenerated_exercise_instances(course, exercise)
    if not instances: # empty
        raise access.config.ConfigError("Exercise is personalized but no exercise instances have been pregenerated")
    if len(instances) == 1:
        # only one instance, must pick that one
        generated_dir = instances[0]
    else:
        while generated_dir == old_instance:
            generated_dir = random.choice(instances)
    
    pregenerated_dir = pregenerated_exercises_directory_path(course, exercise)
    generated_dir = os.path.join(pregenerated_dir, generated_dir)
    
    try:
        # link the user to the randomly selected generated exercise instance
        os.symlink(generated_dir, os.path.join(user_dir, 'generated'))
    except OSError:
        pass # the generated link already exists
    