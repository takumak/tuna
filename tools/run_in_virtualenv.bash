#!/bin/bash

set -xe

test ! -d venv && rm -rf venv && tools/make_virtualenv.bash
source venv/bin/activate
platform=$(python -c 'from sys import platform;print(platform)')
if test x"$platform" = darwin; then
  reattach-to-user-namespace python src/tuna.py
else
  python src/tuna.py
fi
deactivate
