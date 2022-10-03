#!/bin/bash

docker build -f .github/workflows/lint.Dockerfile -q . -t aplus_prospector
docker run --rm -v ${PWD}:/app -w /app aplus_prospector sh -c 'prospector'
