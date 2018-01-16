#!/bin/bash
# Orders a container using docker run command. Prerequisites:
# 1. Docker is installed on the computer.
# 2. Mooc-grader must listen at public IP (e.g. runserver 0.0.0.0:8080).
#
# The container must make an HTTP POST request including fields
# points, max_points, and feedback (HTML) to $REC/container-post.

SID=$1
GRADER_HOST=$2
DOCKER_IMAGE=$3
EXERCISE_MOUNT=$4
SUBMISSION_MOUNT=$5
CMD=$6
COURSE_JSON=$7
EXERCISE_JSON=$8

# Override host to enable local testing.
IP=$(ifconfig | grep -Eo 'inet (addr:)?([0-9]*\.){3}[0-9]*' | grep -Eo '([0-9]*\.){3}[0-9]*' | grep -v '127.0.0.1' | head -1)
PORT=${GRADER_HOST##*:}
GRADER_HOST=http://$IP:$PORT

docker run \
  -d --rm \
  -e "SID=$SID" \
  -e "REC=$GRADER_HOST" \
  -v $EXERCISE_MOUNT:/exercise \
  -v $SUBMISSION_MOUNT:/submission \
  $DOCKER_IMAGE \
  $CMD
