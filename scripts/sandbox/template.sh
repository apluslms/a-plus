#!/bin/bash
#
# A template for a sandbox grading script.
#

# Example of picking out a script argument.
source `dirname $0`/_args.sh
OPT=
while args
do
	case "$ARG_ITER" in
		--opt) OPT=$ARG_NEXT; args_skip ;;
		*) ;;
	esac
done

# Example of iterating over words.
LIST=( "$OPT" )
for i in $LIST
do
	echo "OPT=$i"
done

# Print out submission feedback.
echo "Submission directory contents:"
echo ""
ls -lR
echo ""
echo "Always granting 10/10 points."

# Announce points to the grading service.
echo "TotalPoints: 10"
echo "MaxPoints: 10"
