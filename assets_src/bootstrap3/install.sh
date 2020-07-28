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
sed "s,bootstrap/,$NAME/,g" node_modules/bootstrap-sass/assets/stylesheets/_bootstrap.scss \
	> "${DEST_SASS%/*}/_$NAME.scss"
cp -r node_modules/bootstrap-sass/assets/stylesheets/bootstrap "$DEST_SASS"
sed -i "s,bootstrap/,$NAME/,g" "$DEST_SASS/_variables.scss"

echo "Populating ${DEST_FONTS#$ROOT/}"
mkdir -p "${DEST_FONTS%/*}"
rm -rf "$DEST_FONTS"
cp -r node_modules/bootstrap-sass/assets/fonts/bootstrap "$DEST_FONTS"

echo "Populating ${DEST_JS#$ROOT/}"
mkdir -p "$DEST_JS"
rm -f "$DEST_JS/"bootstrap3.*.js
cp node_modules/bootstrap-sass/assets/javascripts/bootstrap.min.js "$DEST_JS/bootstrap3.min.js"
