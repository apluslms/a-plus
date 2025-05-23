#!/bin/sh

NAME="${PWD##*/}"
ROOT="../.."
ASSETS="$ROOT/assets"
DEST_SASS="$ASSETS/sass/vendor/$NAME"

echo "Populating ${DEST_SASS#$ROOT/}"
rm -rf "$DEST_SASS"
mkdir "$DEST_SASS"
cp github.scss "$DEST_SASS/github.scss"
cp github-dark.scss "$DEST_SASS/github-dark.scss"

