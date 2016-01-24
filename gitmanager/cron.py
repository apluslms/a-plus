import sys, os, yaml, json


def read_static_dir(course_dir):
    '''
    Reads static_dir from course configuration.
    '''
    for parser, file_name in (
        (yaml.load, '/index.yaml'),
        (json.load, '/index.json'),
    ):
        if os.path.exists(course_dir + file_name):
            with open(course_dir + file_name) as f:
                content = parser(f.read())
                if 'static_dir' in content:
                    return content['static_dir']
    return ''


def read_log(log_file):
    '''
    Reads a log file.
    '''
    if os.path.exists($log_file):
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
        print('Use 2: {} static $course_dir'.format(argv[0]))


if __name__ == '__main__':
    main(sys.argv)
