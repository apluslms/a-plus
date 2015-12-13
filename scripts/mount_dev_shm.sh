#!/bin/bash
if ! grep --quiet /var/sandbox/dev/shm /etc/fstab
then
	echo "none /var/sandbox/dev/shm tmpfs rw,nosuid,nodev,noexec 0 0" >> /etc/fstab
fi
mount /var/sandbox/dev/shm
