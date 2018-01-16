#!/bin/bash
#
# Converts text file to the given character set.
#
if [ $# -ne 3 ]
then
	echo $0 new-charset file-name temporary-name
	exit 0
fi

FROM=`file -b --mime-encoding $2`
if [ "$FROM" != "binary" ] && [[ "$FROM" != ERROR:* ]]
then
	iconv -f $FROM -t $1 -c $2 > $3
	mv $3 $2
fi
