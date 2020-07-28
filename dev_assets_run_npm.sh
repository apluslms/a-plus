#!/bin/sh

name=${1:-}
shift
dir="assets_src/$name"

if [ -z "$name" ]; then
    echo "usage: $0 assets_package [npm command]"
    echo " e.g.: $0 myscript-js update"
    exit 64
elif ! [ -d "$dir" ]; then
    echo "$dir doesn't exists"
    exit 64
fi

image=$(grep -F 'image: node:' .drone.yml | head -n1 | awk '{print $2}')
[ "$image" ] || exit 2

exec docker run --rm -it --init \
    -u $(id -u):$(id -g) \
    -e XDG_CONFIG_HOME=/tmp/ \
    -e npm_config_cache=/work/node_cache \
    -v "`pwd`:/work:rw" \
    -w "/work/$dir" \
    "$image" \
    npm "$@"
