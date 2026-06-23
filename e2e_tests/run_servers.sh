#!/bin/bash

export COMPOSE_FILE=docker-compose.yml

scriptpath=$(dirname "$(realpath "$0")")

# Move to the directory containing this file
cd "${scriptpath}" || { echo "Failed to move to directory ${scriptpath}!"; exit 1; }

# Clone aplus-manual if it hasn't been cloned yet
if ! [ -d ../../aplus-manual ]; then
    git clone https://github.com/apluslms/aplus-manual.git ../../aplus-manual
    ( cd ../../aplus-manual && git submodule update --init && cd "${scriptpath}" ) || { echo "Failed to initialize and update git submodules!"; exit 1; }
fi

# Run the server
./docker-up.sh
