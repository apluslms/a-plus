#!/bin/bash
# Orders a container using docker-run command.
# The container command is responsible to call /aplus/grade in end.

SID=$1
GRADER_HOST=$2
DOCKER_IMAGE=$3
EXERCISE_MOUNT=$4
SUBMISSION_MOUNT=$5
CMD=$6

# Override host to enable local testing.
IP=$(ifconfig | grep -Eo 'inet (addr:)?([0-9]*\.){3}[0-9]*' | grep -Eo '([0-9]*\.){3}[0-9]*' | grep -v '127.0.0.1' | head -1)
PORT=${GRADER_HOST##*:}
GRADER_HOST=http://$IP:$PORT

eval $(docker-machine env)

docker run \
  -d \
  -e "SID=$SID" \
  -e "REC=$GRADER_HOST" \
  -v $EXERCISE_MOUNT:/exercise \
  -v $SUBMISSION_MOUNT:/submission \
  $DOCKER_IMAGE \
  $CMD
