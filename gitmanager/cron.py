import sys, os


def read_static_dir(course_key):
    '''
    Reads static_dir from course configuration.
    '''
    sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "grader.settings")
    from access.config import ConfigParser
    config = ConfigParser()

    course = config.course_entry(course_key)
    if 'static_dir' in course:
        return course['static_dir']
    return ''


def read_log(log_file):
    '''
    Reads a log file.
    '''
    if os.path.exists(log_file):
        with open(log_file) as f:
            content = f.read()
            content = content.replace('"', '').replace('\'', '')
            content = content.replace('\n', '\\n').replace('\r', '\\t')
            return content
    return ''


def main(argv):
    if len(argv) == 3 and argv[1] == 'log':
        print(read_log(argv[2]))
    elif len(argv) == 3 and argv[1] == 'static':
        print(read_static_dir(argv[2]))
    else:
        print('Use 1: {} log $log_file'.format(argv[0]))
        print('Use 2: {} static $course_key'.format(argv[0]))


if __name__ == '__main__':
    main(sys.argv)
