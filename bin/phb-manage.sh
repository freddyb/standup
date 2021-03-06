#!/bin/bash -ex

# phb-manage.sh runs manage.py with oblivious hand-wavey default settings
# suitable for management commands that will work despite the wildly ignorant
# nature of hand-wavey default settings. this is especially useful for running
# management commands during the docker build process.
#
# Usage: phb-manage.sh [COMMAND] [ARGS]
#
# Example: phb-manage.sh collectstatic --noinput

export DEBUG=False SECRET_KEY=foo DATABASE_URL=sqlite://

python3 manage.py $@
