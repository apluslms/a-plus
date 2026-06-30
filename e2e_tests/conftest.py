import os
import subprocess
import time

import pytest
import requests


@pytest.fixture(scope="session", autouse=True)
def django_server():
    # Start containers
    path = os.path.dirname(os.path.abspath(__file__))
    # pylint: disable-next=consider-using-with
    server_process = subprocess.Popen([os.path.join(path, "run_servers.sh")], stdin=subprocess.PIPE)

    # Wait 2 minutes for the server to be ready
    max_retries = 120
    for _ in range(max_retries):
        try:
            response = requests.get("http://localhost:8010/") # pylint: disable=missing-timeout
            if response.status_code == 200:
                # Trigger course build in gitmanager container
                print("A+ server is ready. Initializing and building aplus-manual course via gitmanager...")
                env = os.environ.copy()
                env["COMPOSE_FILE"] = "docker-compose.yml"
                env["COMPOSE_PROJECT_NAME"] = "aplus-e2e"

                try:
                    subprocess.run(
                        [
                            "docker", "compose", "exec", "-T", "-u", "gitmanager", "gitmanager",
                            "python3", "manage.py", "shell", "-c",
                            "from builder.models import Course, CourseUpdate; "
                            "from builder.builder import push_event; "
                            "course = Course.objects.get(key='default'); "
                            "CourseUpdate.objects.create(course=course, status='PENDING', request_ip='127.0.0.1'); "
                            "push_event('default')"
                        ],
                        cwd=path,
                        env=env,
                        check=True
                    )
                    print("Default course successfully built on gitmanager and A+ notified!")
                except subprocess.CalledProcessError as e:
                    print(f"Failed to build default course via gitmanager: {e}")

                # Wait a bit more to let the server settle (tests may fail otherwise)
                time.sleep(10)
                break
        except requests.ConnectionError:
            pass

        time.sleep(1)

    # Run tests
    yield

    # Stop containers and remove data
    server_process.communicate(input=b'q')
