#!/bin/sh
SID=$1
GRADER_HOST=$2
DOCKER_IMAGE=$3
EXERCISE_MOUNT=$4
SUBMISSION_MOUNT=$5
CMD=$6

ssh -o StrictHostKeyChecking=no grader@kubem "/home/grader/run-scala-grader.sh $SID $GRADER_HOST $DOCKER_IMAGE $EXERCISE_MOUNT $SUBMISSION_MOUNT"
