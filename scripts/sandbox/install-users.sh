#!/bin/bash
#
# Adds sandbox users. Required.
#
if ! grep --quiet 666 /etc/passwd
then
	useradd -u 666 -ms /bin/bash sandbox
fi
if ! grep --quiet 667 /etc/passwd
then
	useradd -u 667 -ms /bin/bash sandboxnet
fi
