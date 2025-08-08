#!/bin/sh

NAME="${PWD##*/}"
ROOT="../.."
ASSETS="$ROOT/assets"
DEST_JS="$ASSETS/js/"
DEST_SASS="$ASSETS/sass/vendor/$NAME"
DEST_FONTS="$ASSETS/fonts/$NAME"

echo "Populating ${DEST_SASS#$ROOT/}"
mkdir -p "${DEST_SASS%/*}"
rm -rf "$DEST_SASS"
# Change import paths in _bootstrap5.scss to include a "bootstrap5/" prefix
# since the scss files to be imported are placed in this subdirectory in the next step
sed 's,@import ",@import "'"$NAME"'/,g' node_modules/bootstrap/scss/bootstrap.scss \
	> "${DEST_SASS%/*}/_$NAME.scss"
cp -r node_modules/bootstrap/scss "$DEST_SASS"

echo "Populating ${DEST_JS#$ROOT/}"
mkdir -p "$DEST_JS"
rm -f "$DEST_JS/$NAME".*.js
cp node_modules/bootstrap/dist/js/bootstrap.min.js "$DEST_JS/$NAME.min.js"
cp node_modules/@popperjs/core/dist/umd/popper.min.js "$DEST_JS/popper.min.js"