#!/bin/bash

# Build the image if it doesn't exist yet
if [ -z "$(docker images -q aplus_prospector 2> /dev/null)" ]; then
  echo "Building prospector image..."
  docker build -f .github/workflows/lint.Dockerfile -q . -t aplus_prospector
else
  echo "Using existing prospector image."
fi
echo "Running prospector..."
docker run --rm -v "${PWD}":/app -w /app aplus_prospector sh -c 'prospector'
