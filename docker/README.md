# run-aplus-front

A Docker container that runs the A-plus
Learning Management System exposed to port 8000.

Note that the A-plus front service alone does not provide
capability to implement or host learning material or exercises.
The front connects to different material or assessment services
that provide interactive content to learners. A common
counterpart for content services is the
[A-plus MOOC-grader](https://hub.docker.com/r/apluslms/run-mooc-grader/).

See into the [A-plus manual course](https://github.com/apluslms/aplus-manual)
that includes a Docker compose configuration to develop and test course content.

## Usage

A-plus is installed in `/srv/aplus`.
You can mount development version of the source code to `/src/aplus`.
The container will then copy it to `/srv/aplus` and compile
the translation file (django.mo). If you mount directly to
`/srv/aplus`, you need to manually compile the translation file beforehand,
but on the other hand, Django can reload the code and restart the server
without restarting the whole container when you edit the source code files.

You can mount development version of the A+ source code on top of that, if you wish.

Location `/data` is a volume and contains submission files, database and secret key.
It is world writable, so you can run this container as normal user.

The environment variable `APLUS_ENABLE_DJANGO_DEBUG_TOOLBAR` can be set to `'true'` or `'false'` in `docker-compose.yml`.
It controls the Django Debug Toolbar, which provides useful debug data in a set panels on the right side of the web pages.
The debug data comes from the a-plus code, not from course contents or exercise graders.
Therefore, the toolbar is useful to A+ platform developers.
If there is a reason to disable the toolbar (e.g., in some cases, it might slow down the performance),
then it is easy to switch it on or off with the environment variable.
By default when the env variable is not defined, the toolbar is disabled.

Partial example of `docker-compose.yml` (volumes are optional of course):

```yaml
services:
  plus:
    image: apluslms/run-aplus-front
    environment:
      APLUS_ENABLE_DJANGO_DEBUG_TOOLBAR: 'true'
    volumes:
    # named persistent volume (until removed)
    # - data:/data
    # mount development version to /src/aplus
    # - /home/user/a-plus/:/src/aplus/:ro
    # or to /srv/aplus
    # - /home/user/a-plus/:/srv/aplus/:ro
    ports:
      - "8000:8000"
    depends_on:
      - grader
volumes:
  data:
```
