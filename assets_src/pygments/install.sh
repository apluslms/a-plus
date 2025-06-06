#!/bin/sh

NAME="${PWD##*/}"
ROOT="../.."
ASSETS="$ROOT/assets"
DEST_SASS="$ASSETS/sass/vendor/$NAME"

echo "Populating ${DEST_SASS#$ROOT/}"
rm -rf "$DEST_SASS"
mkdir "$DEST_SASS"
cp default.scss "$DEST_SASS/default.scss"
cp github-dark.scss "$DEST_SASS/github-dark.scss"

