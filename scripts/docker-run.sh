#!/bin/bash
# Orders a container using docker-run command.

SID=$1
DOCKER_IMAGE=$2
EXERCISE_MOUNT=$3
SUBMISSION_MOUNT=$4
CMD=$5

echo "TODO $DOCKER_IMAGE mounting ($EXERCISE_MOUNT and $SUBMISSION_MOUNT): $CMD"
