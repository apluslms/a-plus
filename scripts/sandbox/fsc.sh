#!/bin/bash
#
# Controls the scala fsc compiler service which can speed up
# scala compilations a lot. Requires install-scala-[version].sh
#
PORT=30000

if [ "$1" == "--check" ] || [ "$1" == "--quietcheck" ]; then
	netstat -n -l | grep -q $PORT
	if [ $? -eq 0 ]; then
		if [ "$1" != "--quietcheck" ]; then
    		echo "Server already running..."
    	fi
		exit 0
	fi
fi

echo "Killing the old fsc..."
fsc -port $PORT -shutdown
sleep 1
pkill -f ".* scala.tools.nsc.CompileServer"
rm -rf /tmp/scala-develsandbox/scalac-compile-server-port

if [ "$1" != "--shutdown" ]
then
  echo "Starting the new one..."
	fsc -port $PORT -max-idle 0
fi
