import os
import time

from django.conf import settings


LOCK_FILE = "/tmp/grader-affinity-lock"
LOCK_MAX_TIME = 30
AFFINITY_FILE = "/tmp/grader-affinity"


def set_affinity(affinities):
    """ Sets process affinity to configured processor cores. """
    affinities_n = len(affinities)
    if affinities_n > 0:
        my_pid = os.getpid()
        try:
            get_lock(my_pid)
            pids = [0] * affinities_n
            if os.path.exists(AFFINITY_FILE):
                with open(AFFINITY_FILE, 'r') as f:
                    for i,line in enumerate(f):
                        if i < affinities_n:
                            pids[i] = int(line.strip())
            for i,pid in enumerate(pids):
                if pid in (0, my_pid) or not process_exists(pid):
                    aff = affinities[i]
                    os.sched_setaffinity(0, aff)
                    print("SET AFFINITY: {}".format(str(aff)))
                    pids[i] = my_pid
                    break

            with open(AFFINITY_FILE, 'w') as f:
                f.write("\n".join([str(i) for i in pids]))

        finally:
            release_lock(my_pid)


def get_lock(pid):
    while os.path.exists(LOCK_FILE):
        time.sleep(1)
        if time.time() - os.path.getmtime(LOCK_FILE) > LOCK_MAX_TIME:
            os.remove(LOCK_FILE)
    with open(LOCK_FILE, 'w') as f:
        f.write(str(pid))


def release_lock(pid):
    if os.path.exists(LOCK_FILE):
        lock_pid = None
        with open(LOCK_FILE, 'r') as f:
            lock_pid = f.read().strip()
        if lock_pid == str(pid):
            os.remove(LOCK_FILE)


def process_exists(pid):
    """ Checks if a process exists. """
    try:
        os.kill(pid, 0)
    except OSError:
        return False
    return True
