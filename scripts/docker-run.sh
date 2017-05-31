#!/bin/bash
# Orders a container using docker-run command.
# The container command is responsible to call /aplus/grade in end.

SID=$1
GRADER_HOST=$2
DOCKER_IMAGE=$3
EXERCISE_MOUNT=$4
SUBMISSION_MOUNT=$5
CMD=$6

docker run \
  --rm \
  -e "SID=$SID" \
  -e "REC=$GRADER_HOST" \
  -v $EXERCISE_MOUNT:/exercise \
  -v $SUBMISSION_MOUNT:/submission \
  $DOCKER_IMAGE \
  $CMD
