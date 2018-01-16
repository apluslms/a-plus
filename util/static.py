import os
from django.conf import settings

def symbolic_link(courses_dir, course):
    dst = os.path.join(settings.BASE_DIR, 'static', course['key'])
    if not os.path.lexists(dst) and 'static_dir' in course:
        src = os.path.join(courses_dir, course['key'], course['static_dir'])
        os.symlink(src, dst)
