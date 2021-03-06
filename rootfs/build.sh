#!/usr/bin/env bash

# fail on any command exiting non-zero
set -eo pipefail

if [[ -z $DOCKER_BUILD ]]; then
  echo
  echo "Note: this script is intended for use by the Dockerfile and not as a way to build the controller locally"
  echo
  exit 1
fi

# install required system packages
apk add --update-cache \
  build-base \
  curl \
  libffi-dev \
  libpq \
  postgresql-dev \
  python3 \
  python3-dev \
  git

# Symlink python3 binary to python
ln -s /usr/bin/python3 /usr/bin/python

# install pip
curl -sSL https://raw.githubusercontent.com/pypa/pip/7.1.2/contrib/get-pip.py | python -

# add a deis user
adduser deis -D -h /app -s /bin/bash

# create a /app directory for storing application data
mkdir -p /app && chown -R deis:deis /app

# create directory for confd templates
mkdir -p /templates && chown -R deis:deis /templates

# install dependencies
pip install --disable-pip-version-check --no-cache-dir -r /app/requirements.txt

# cleanup.
apk del --purge \
  build-base \
  curl \
  libffi-dev \
  postgresql-dev \
  python3-dev \
  git
rm -rf /var/cache/apk/*
