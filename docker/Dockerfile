FROM apluslms/service-base:django-1.19

# Set container related configuration via environment variables
ENV CONTAINER_TYPE="aplus" \
    APLUS_LOCAL_SETTINGS="/srv/aplus-cont-settings.py" \
    APLUS_SECRET_KEY_FILE="/local/aplus/secret_key.py" \
    USE_GITMANAGER="false"

RUN : \
 && apt_install \
      python3-lxml \
      python3-lz4 \
      python3-pillow \
      redis \
\
  # create user
 && adduser --system --no-create-home --disabled-password --gecos "A+ webapp server,,," --home /srv/aplus --ingroup nogroup aplus \
 && mkdir /srv/aplus && chown aplus.nogroup /srv/aplus \
 && git config --global --add safe.directory /srv/aplus \
 && :

COPY docker/rootfs /
COPY . /srv/aplus

RUN cd /srv/aplus \
  # prebuild .pyc files
 && python3 -m compileall -q . \
  # install requirements, remove the file, remove unrequired locales and tests
 && pip_install \
      -r requirements.txt \
      "django-debug-toolbar >= 6.1.0, < 7" \
      flower \
 && rm requirements.txt \
 && find /usr/local/lib/python* -type d -regex '.*/locale/[a-z_A-Z]+' -not -regex '.*/\(en\|fi\|sv\)' -print0 | xargs -0 rm -rf \
 && find /usr/local/lib/python* -type d -name 'tests' -print0 | xargs -0 rm -rf \
\
  # preprocess
 && export \
    APLUS_SECRET_KEY="-" \
    APLUS_CACHES="{\"default\": {\"BACKEND\": \"django.core.cache.backends.dummy.DummyCache\"}}" \
 && python3 manage.py compilemessages 2>&1 \
 && create-db.sh aplus aplus django-migrate.sh \
 \
 && mkdir -p /var/celery/results \
 && chown -R aplus:nogroup /var/celery \
 && :


WORKDIR /srv/aplus
EXPOSE 8000
EXPOSE 5555
CMD [ "manage", "runserver", "0.0.0.0:8000" ]
