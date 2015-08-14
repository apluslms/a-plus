#!/bin/bash
#
# Runs the /usr/local/sandbox/install-* scripts and then
# selected /usr/local/sandbox/[course]/install-* scripts
# in aplhabetical order.
#
PATH=$PATH:/usr/local/bin:/usr/local/sbin

function echo_err
{
	echo -e "\e[0;31m$1\e[0m"
}
function echo_ok
{
	echo -e "\e[0;32m$1\e[0m"
}

echo_ok "*** Installing wget in chroot"
apt-get -qy install wget

echo_ok "*** Running individual installation scripts"

FILES=`find /usr/local/sandbox -maxdepth 1 -name install-\*`
if [ "$1" == "all" ]
then
	FILES="$FILES `find /usr/local/sandbox -mindepth 2 -name install-\*`"
else
	FILES="$FILES `find /usr/local/sandbox/$1 -name install-\*`"
fi

for file in $FILES
do
	echo_ok "*** Running ${file}"
	$file $2
	RES=$?
	if [ $RES -ne 0 ]
	then
		echo_err "*** ERROR, fix the problem and run again!"
		exit $RES
	fi
done

echo_ok "*** Installation scripts succesfully finished"
