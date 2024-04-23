#!/bin/bash

# This script can be used to stop the containers started by run_servers.sh

export COMPOSE_FILE=docker-compose.yml
export COMPOSE_PROJECT_NAME=aplus

docker compose down --volumes --remove-orphans
