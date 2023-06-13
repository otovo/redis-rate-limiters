# See https://just.systems/man/en/ for docs

# List available commands
default:
    just --list

setup:
    just teardown
    docker compose up -d
    ./setup-cluster.sh

teardown:
    docker compose down --volumes
