'''
Utility functions for exercise files.

'''
from django.conf import settings
import datetime, random, string, os, shutil


def create_submission_dir(course, exercise):
    '''
    Creates a directory for a submission.

    @type course: C{dict}
    @param course: a course configuration
    @type exercise: C{dict}
    @param exercise: an exercise configuration
    @rtype: C{str}
    @return: directory path
    '''

    # Create a unique directory name for the submission.
    d = datetime.datetime.now().strftime("%Y%m%d%H%M%S%f")
    d += ''.join([random.choice(string.ascii_letters) for _ in range(5)])
    submission_dir = os.path.join(settings.SUBMISSION_PATH,
        course["key"], exercise["key"], d)

    # Create empty directory.
    if not os.path.exists(submission_dir):
        os.makedirs(submission_dir)

    return submission_dir


def clean_submission_dir(submission_dir):
    '''
    Cleans a submission directory after grading.

    @type submission_dir: C{str}
    @param submission_dir: directory path
    '''
    if submission_dir.startswith(settings.SUBMISSION_PATH):
        shutil.rmtree(submission_dir)


def save_submitted_file(submission_dir, file_name, post_file):
    '''
    Saves a submitted file to a submission directory.

    @type submission_dir: C{str}
    @param submission_dir: directory path
    @type file_name: C{str}
    @param file_name: a file name to write
    @type post_file: C{django.core.files.uploadedfile.UploadedFile}
    @param post_file: an uploaded file to save
    '''
    file_path = submission_file_path(submission_dir, file_name)
    with open(file_path, "wb+") as f:
        for chunk in post_file.chunks():
            f.write(chunk)
        f.close()


def write_submission_file(submission_dir, file_name, content):
    '''
    Writes a submission file to a submission directory.

    @type submission_dir: C{str}
    @param submission_dir: directory path
    @type file_name: C{str}
    @param file_name: a file name to write
    @type content: C{str}
    @param content: content to write
    '''
    file_path = submission_file_path(submission_dir, file_name)
    with open(file_path, "w+") as f:
        f.write(content)
        f.close()


def submission_file_path(submission_dir, file_name):
    '''
    Creates a submission file path.

    @type submission_dir: C{str}
    @param submission_dir: directory path
    @type file_name: C{str}
    @param file_name: a file name to write
    @rtype: C{str}
    @return: a submission file path
    '''
    if not is_safe_file_name(file_name):
        raise ValueError("Unsafe file name detected")
    file_path = os.path.join(submission_dir, 'user', file_name)
    dir_path = os.path.dirname(file_path)
    if not os.path.exists(dir_path):
        os.makedirs(dir_path)
    return file_path


def is_safe_file_name(file_name):
    '''
    Checks that a file name is safe for concatenating to some path.

    @type file_name: C{str}
    @param file_name: a file name
    '''
    if file_name == "" or file_name == "." or file_name.startswith("/") or ".." in file_name:
        return False
    return True
