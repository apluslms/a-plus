#!/bin/sh

image=$(grep -F 'image: apluslms/develop-sass' .drone.yml | head -n1 | awk '{print $2}')
[ "$image" ] || exit 2

exec docker run --rm -it \
    -u $(id -u):$(id -g) \
    -v "`pwd`:/work:rw" \
    -w '/work' \
    "$image" \
    sass --watch assets/sass:assets/css --poll
