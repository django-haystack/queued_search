#!/bin/sh

# Setup the environment
export PYTHONPATH=`pwd`:`pwd`/../
export DJANGO_SETTINGS_MODULE=settings

# Run our sample ``notes`` app, where all the tests are located.
django-admin.py test notes
