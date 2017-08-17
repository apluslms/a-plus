#!/bin/bash
# Orders a container using docker run command.
# The container command is responsible to call /aplus/grade in end.

SID=$1
GRADER_HOST=$2
DOCKER_IMAGE=$3
EXERCISE_MOUNT=$4
SUBMISSION_MOUNT=$5
CMD=$6

# Manage for docker-compose setup, see test course for reference.
TMP=/tmp/aplus
TMP_EXERCISE_MOUNT=$TMP/_ex/${EXERCISE_MOUNT##/srv/courses/}
TMP_SUBMISSION_MOUNT=$TMP/${SUBMISSION_MOUNT##/srv/uploads/}
mkdir -p $(dirname $TMP_EXERCISE_MOUNT)
mkdir -p $(dirname $TMP_SUBMISSION_MOUNT)
cp -r $EXERCISE_MOUNT $TMP_EXERCISE_MOUNT
cp -r $SUBMISSION_MOUNT $TMP_SUBMISSION_MOUNT

docker run \
  -d \
  -e "SID=$SID" \
  -e "REC=$GRADER_HOST" \
  -v $TMP_EXERCISE_MOUNT:/exercise \
  -v $TMP_SUBMISSION_MOUNT:/submission \
  $DOCKER_IMAGE \
  $CMD
