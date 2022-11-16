#!/bin/bash

docker build -f .github/workflows/lint.Dockerfile -q . -t aplus_prospector
docker run -v ${PWD}:/app -w /app aplus_prospector sh -c 'prospector'
docker rm $(docker stop $(docker ps -a -q --filter ancestor=aplus_prospector --format="{{.ID}}"))
