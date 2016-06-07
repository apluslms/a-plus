#!/bin/bash
#
# Utility functions for copying files or directories given as path->path lists.
# Usage:
# Set list variable before calling copy_paths. The variable contains a list of
# path->path strings. Call copy_paths with two arguments: the first is the base
# directory for source files and the second is the base directory for the destination.

function next_paths
{
	if [ "${list[$list_pos]}" ]; then
		entry=${list[$list_pos]}
		IF=${entry%\?*}
		entry=${entry#\?*}
		SRC=$1${entry%->*}
		TO=$2${entry#*->}
		if [[ $entry == *".."* ]] || [ "$SRC" == "" -o "$TO" == "" ]; then
			echo "Invalid directive $entry" >&2
			exit 1
		fi
		let list_pos+=1
		return 0
	fi
	return 1
}
function copy_paths
{
	list_pos=0
	while next_paths $1 $2; do
		if [ -d $SRC ]; then
			mkdir -p $TO
			find $SRC -mindepth 1 -maxdepth 1 -exec cp -r {} $TO \;
		elif [ -f $SRC ]; then
			mkdir -p `dirname $TO`
			cp $SRC $TO
		elif [ "$IF" != "" ]; then
			echo "Copy source not found $SRC IF=$IF" >&2
			exit 1
		fi
	done
}
