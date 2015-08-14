#!/bin/bash
#
# Converts text file to the given character set.
#
if [ $# -ne 3 ]
then
	echo $0 new-charset file-name temporary-name
	exit 0
fi

INFO=`file -i $2`
FROM=${INFO##*charset=}
if [ "$FROM" != "binary" ]
then
	iconv -f $FROM -t $1 -c $2 > $3
	mv $3 $2
fi
