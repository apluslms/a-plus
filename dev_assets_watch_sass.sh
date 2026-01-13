#!/bin/sh

image="apluslms/develop-sass:1"

exec docker run --rm -it \
    -u $(id -u):$(id -g) \
    -v "`pwd`:/work:rw" \
    -w '/work' \
    "$image" \
    sass --watch assets/sass:assets/css --poll
