#!/bin/bash

FILE=server.ports

cd `dirname "$0"`
if [ -r "$FILE" ]; then 
	echo "Killing servers."
	kill `cat $FILE`
	rm $FILE
fi
