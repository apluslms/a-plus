#!/bin/sh
SID=$1
GRADER_HOST=$2
DOCKER_IMAGE=$3
EXERCISE_MOUNT=$4
SUBMISSION_MOUNT=$5
CMD=$6

ssh -o StrictHostKeyChecking=no grader@k8s-admin.cs.hut.fi "/home/grader/run-grader.sh $SID $GRADER_HOST $DOCKER_IMAGE $EXERCISE_MOUNT $SUBMISSION_MOUNT '$CMD'"
