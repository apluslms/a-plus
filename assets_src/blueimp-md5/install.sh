#!/bin/sh

NAME="${PWD##*/}"
ROOT="../.."
ASSETS="$ROOT/assets"
DEST_JS="$ASSETS/js/"

echo "Populating ${DEST_JS#$ROOT/}"
mkdir -p "$DEST_JS"
rm -f "$DEST_JS/"md5.*.js
cp node_modules/blueimp-md5/js/md5.min.js "$DEST_JS/md5.min.js"
cp node_modules/blueimp-md5/js/md5.min.js.map "$DEST_JS/md5.min.js.map"
