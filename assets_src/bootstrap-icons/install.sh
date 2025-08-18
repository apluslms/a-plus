#!/bin/sh

NAME="${PWD##*/}"
ROOT="../.."
ASSETS="$ROOT/assets"
DEST_FONTS="$ASSETS/fonts/$NAME"
DEST_SASS="$ASSETS/sass/vendor/$NAME"

echo "Populating ${DEST_FONTS#$ROOT/}"
mkdir -p "$ASSETS/fonts"
mkdir -p "$DEST_FONTS"
mkdir -p "$DEST_SASS"
rm -f "$DEST_FONTS/*"
rm -f "$DEST_FONTS/fonts/*"
cp -r node_modules/bootstrap-icons/font/* "$DEST_FONTS/"
cp -r node_modules/bootstrap-icons/font/* "$DEST_SASS/"
