#!/bin/bash
#
# Provides functions to iterate over script arguments:
#

ARG_ARR=("$@")
ARG_POS=0

function args_skip
{
	let ARG_POS+=1
}

# Travel each argument at time.
function args
{
	# End when getting empty arguments, array is finished
	if [ "${ARG_ARR[ARG_POS]}" ]
	then
		ARG_ITER=${ARG_ARR[ARG_POS]}
		args_skip
		ARG_NEXT=${ARG_ARR[ARG_POS]}
		return 0
	fi
	return 1
}

# Check argument is set.
function args_require
{
	if [ "$2" = "" ]
	then
		echo "$1 is missing" >&2
		exit 1
	fi
}

# Check directory is ok.
function args_require_dir
{
	args_require $1 $2
	if [ ! -d $2 ]
	then
		echo "Directory not found: $2" >&2
		exit 1
	fi
}

# Check argument is logically set true.
function args_true
{
	[ "$1" == "1" ] || [ "$1" == "on" ] || [ "$1" == "true" ] || [ "$1" == "yes" ]
	return $?
}
